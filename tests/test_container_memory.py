import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location('container_memory', Path(__file__).resolve().parents[1] / 'scripts/container-memory.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class ContainerMemoryTests(unittest.TestCase):
    def test_reads_container_scope_including_swapped_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proc = root / 'proc/42'
            proc.mkdir(parents=True)
            (proc / 'cgroup').write_text('0::/system.slice/docker-example.scope\n')
            scope = root / 'cgroup/system.slice/docker-example.scope'
            scope.mkdir(parents=True)
            for name, value in [('memory.current', '10485760'), ('memory.swap.current', '209715200'), ('memory.max', 'max')]:
                (scope / name).write_text(value + '\n')
            self.assertEqual(report.memory_usage(root / 'proc', root / 'cgroup', 42),
                             {'memory': 10485760, 'swap': 209715200, 'limit': 'max'})

    def test_rejects_cgroup_v1_instead_of_reporting_zero_swap(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '42').mkdir()
            (root / '42/cgroup').write_text('5:memory:/docker/example\n')
            with self.assertRaisesRegex(ValueError, 'cgroup-v2'):
                report.memory_usage(root, root, 42)


if __name__ == '__main__':
    unittest.main()

