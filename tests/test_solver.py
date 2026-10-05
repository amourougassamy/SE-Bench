import unittest

from se_bench.solver import available, solve


def cantilever():
    return {"revision": "A", "units": "N-m-Pa", "analysis": "linear_static_2d",
            "nodes": {"1": [0.0, 0.0], "2": [3.0, 0.0]},
            "sections": {"S": {"A_m2": 0.02, "E_Pa": 200e9, "I_m4": 8e-5}},
            "elements": {"1": {"nodes": ["1", "2"], "section": "S"}},
            "supports": {"1": [1, 1, 1]},
            "load_case": {"name": "TEST", "nodal": {"2": [0, -10000.0, 0]}, "uniform": {}}}


@unittest.skipUnless(available(), "Install .[solver] for real solver integration checks")
class SolverTests(unittest.TestCase):
    def test_cantilever_against_closed_form(self):
        model = cantilever()
        result = solve(model)
        expected = -10000 * 3**3 / (3 * 200e9 * 8e-5)
        self.assertAlmostEqual(result["displacements"]["2"][1], expected, places=12)
        self.assertAlmostEqual(result["reactions"]["1"][1], 10000, places=6)
        self.assertAlmostEqual(result["reactions"]["1"][2], 30000, places=6)
        self.assertLess(max(abs(v) for v in result["equilibrium_residual_Fx_Fy_Mz"]), 1e-6)

    def test_uniform_load_and_process_isolation(self):
        model = cantilever()
        model["load_case"]["nodal"] = {}
        model["load_case"]["uniform"] = {"1": -5000.0}
        result = solve(model)
        expected = -5000 * 3**4 / (8 * 200e9 * 8e-5)
        self.assertAlmostEqual(result["displacements"]["2"][1], expected, places=12)
        self.assertAlmostEqual(result["reactions"]["1"][1], 15000, places=6)
        self.assertEqual(solve(cantilever())["model_sha256"], solve(cantilever())["model_sha256"])

    def test_rotated_local_uniform_load_equilibrium(self):
        model = cantilever()
        model["nodes"]["2"] = [0, 3]
        model["load_case"]["nodal"] = {}
        model["load_case"]["uniform"] = {"1": 5000}
        result = solve(model)
        self.assertAlmostEqual(result["reactions"]["1"][0], 15000, places=6)
        self.assertLess(max(abs(v) for v in result["equilibrium_residual_Fx_Fy_Mz"]), 1e-6)


if __name__ == "__main__":
    unittest.main()
