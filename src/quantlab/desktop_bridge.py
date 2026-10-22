"""Local desktop JSON protocol. Only trusted, user-owned Python strategies are supported."""
from __future__ import annotations
import contextlib
import csv
import hashlib
from itertools import islice
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
import uuid


def scoped(root, name, folders, suffixes=None):
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not any(path.is_relative_to((root / folder).resolve()) for folder in folders):
        raise ValueError('File is outside the allowed workspace directories')
    if suffixes and path.suffix not in suffixes:
        raise ValueError('Unsupported file type')
    return path


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def json_safe(value):
    import math
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path):
    return json.loads(path.read_text())


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.desktop-')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def resolve_config(root, data):
    from quantlab.config import Config
    c = Config.model_validate(data)
    c.strategy.path = scoped(root, str(c.strategy.path), ['strategies'], {'.py'})
    c.strategy.factor_paths = {name: scoped(root, str(p), ['factors'], {'.py'}) for name, p in c.strategy.factor_paths.items()}
    if c.data.provider != 'yahoo':
        c.data.path = scoped(root, str(c.data.path), ['data'], {'.parquet', '.csv'})
    c.report.runs_dir = root / 'runs'
    c.report.enabled = True
    c.report.open_after_run = False
    return c


def dispatch(root, request):
    action = request['action']
    if action == 'catalog':
        def entries(folder, suffixes):
            base = (root / folder).resolve()
            if not base.is_relative_to(root):
                return []
            return sorted(str(p.relative_to(root)) for p in (root / folder).rglob('*') if p.is_file() and p.suffix in suffixes and not p.name.startswith('.') and '__pycache__' not in p.parts and p.resolve().is_relative_to(base))
        return {'root': str(root), 'strategies': entries('strategies', {'.py'}), 'factors': entries('factors', {'.py'}), 'configs': entries('configs', {'.yaml', '.yml'}), 'data': [{'path': name, 'bytes': (root / name).stat().st_size} for name in entries('data', {'.csv', '.parquet'})]}
    if action == 'read':
        path = scoped(root, request['path'], ['strategies', 'factors'], {'.py'})
        return {'text': path.read_text(), 'hash': fingerprint(path)}
    if action == 'save':
        path = scoped(root, request['path'], ['strategies', 'factors'], {'.py'})
        if fingerprint(path) != request.get('hash'):
            raise ValueError('文件已在外部修改，请重新打开后合并更改；未覆盖磁盘文件。')
        text = request['text']
        if len(text.encode()) > 2_000_000:
            raise ValueError('文件超过 2 MB 限制')
        atomic_write(path, text)
        return {'hash': fingerprint(path)}
    if action == 'config':
        from quantlab.config import load_config
        path = scoped(root, request['path'], ['configs'], {'.yaml', '.yml'})
        c = load_config(path).model_dump(mode='json')
        def relative(p):
            resolved = Path(p).resolve()
            return str(resolved.relative_to(root)) if resolved.is_relative_to(root) else str(resolved)
        c['strategy']['path'] = relative(c['strategy']['path'])
        c['strategy']['factor_paths'] = {k: relative(v) for k, v in c['strategy']['factor_paths'].items()}
        c['data']['path'] = relative(c['data']['path'])
        return c
    if action == 'validate':
        from quantlab.strategy.validator import validate_strategy
        c = resolve_config(root, request['config'])
        with contextlib.redirect_stdout(sys.stderr):
            meta = validate_strategy(c.strategy.path, c.strategy.params, c.universe.symbols, c.strategy.factor_paths, c.data.benchmark, c.execution.sizing)
        return {'message': '策略接口、语法与样例运行校验通过', 'meta': meta}
    if action == 'prepare':
        c = resolve_config(root, request['config'])
        job_id = uuid.uuid4().hex
        job = root / '.quantlab-desktop' / 'jobs' / job_id
        job.mkdir(parents=True)
        # Freeze editable source before the UI can change it for the next experiment.
        frozen = c.model_copy(deep=True)
        frozen.strategy.path = job / c.strategy.path.name
        frozen.strategy.path.write_bytes(c.strategy.path.read_bytes())
        frozen.strategy.factor_paths = {}
        for i, (name, path) in enumerate(c.strategy.factor_paths.items()):
            dst = job / f'factor-{i}.py'
            dst.write_bytes(path.read_bytes())
            frozen.strategy.factor_paths[name] = dst
        atomic_write(job / 'config.json', json.dumps(frozen.model_dump(mode='json')))
        atomic_write(job / 'original.json', json.dumps(c.model_dump(mode='json')))
        return {'id': job_id, 'directory': str(job)}
    if action == 'run':
        from quantlab.archive import archive_run
        from quantlab.config import Config
        job_id = request['id']
        if len(job_id) != 32 or any(ch not in '0123456789abcdef' for ch in job_id):
            raise ValueError('Invalid job ID')
        job = root / '.quantlab-desktop' / 'jobs' / job_id
        try:
            c = Config.model_validate(read_json(job / 'config.json'))
            with contextlib.redirect_stdout(sys.stderr):
                run, result = archive_run(c)
            payload = {'status': 'complete', 'run_id': run.name, 'metrics': result.metrics}
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            payload = {'status': 'failed', 'error': str(exc)}
        atomic_write(job / 'result.json', json.dumps(json_safe(payload), ensure_ascii=False))
        return payload
    if action == 'history':
        items = []
        for run in sorted((root / 'runs').glob('*'), reverse=True):
            if not run.is_dir():
                continue
            # A damaged archive must not prevent browsing the other runs.
            try:
                scoped(root, str(run), ['runs'])
                if (run / 'failure.json').exists():
                    failure = read_json(run / 'failure.json')
                    items.append({**failure, 'id': run.name, 'status': 'failed'})
                elif (run / 'summary.json').exists() and (run / 'metadata.json').exists():
                    summary = read_json(run / 'summary.json')
                    metadata = read_json(run / 'metadata.json')
                    if not isinstance(summary, dict) or not isinstance(metadata, dict):
                        raise ValueError('Archive summary and metadata must be JSON objects')
                    if metadata.get('status') != 'complete':
                        raise ValueError('Archive is not marked complete')
                    items.append({**summary, 'id': run.name, 'status': 'complete'})
            except (OSError, ValueError, TypeError) as exc:
                items.append({'id': run.name, 'status': 'failed', 'error': f'Archive unreadable: {exc}'})
        return items[:100]
    if action in {'result', 'report'}:
        run = scoped(root, 'runs/' + request['id'], ['runs'])
        if run.parent != root / 'runs':
            raise ValueError('Invalid run ID')
        if action == 'report':
            return {'html': (run / 'report.html').read_text()}
        def records(name, limit=None):
            path = run / name
            if not path.exists():
                return []
            with path.open() as f:
                reader = csv.DictReader(f)
                return list(reader if limit is None else islice(reader, limit))
        return {'summary': read_json(run / 'summary.json'), 'equity': records('equity.csv'), 'benchmark': records('benchmark.csv'), 'fills': records('fills.csv', 2000), 'warnings': read_json(run / 'warnings.json'), 'metadata': read_json(run / 'metadata.json')}
    raise ValueError('Unknown desktop action')


def main():
    try:
        root = Path(sys.argv[1]).expanduser().resolve()
        if not (root / 'pyproject.toml').is_file() or not (root / 'src/quantlab').is_dir():
            raise ValueError('请选择包含 pyproject.toml 和 src/quantlab 的 QuantLab 工作区')
        request = json.load(sys.stdin)
        result = dispatch(root, request)
        print(json.dumps({'ok': True, 'data': json_safe(result)}, ensure_ascii=False, allow_nan=False))
    except Exception as exc:
        error = {'message': str(exc), 'type': type(exc).__name__}
        if isinstance(exc, SyntaxError):
            error.update(line=exc.lineno, file=exc.filename)
        print(json.dumps({'ok': False, 'error': error}, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
