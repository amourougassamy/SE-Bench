from copy import deepcopy
import unittest

from se_bench.model import ContractError, digest, load_resultant, validate_model
from se_bench.task import load_task


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.model = deepcopy(load_task()[1])

    def test_initial_contract_and_total_loads(self):
        self.assertTrue(validate_model(self.model)["valid"])
        self.assertEqual(load_resultant(self.model), [20000.0, -120000.0, -440000.0])

    def test_hash_is_order_independent_and_revision_sensitive(self):
        self.assertEqual(digest(self.model), digest(dict(reversed(list(self.model.items())))))
        other = deepcopy(self.model)
        other["revision"] = "B"
        self.assertNotEqual(digest(self.model), digest(other))

    def test_rejects_unit_mismatch(self):
        self.model["units"] = "kip-in"
        with self.assertRaises(ContractError):
            validate_model(self.model)

    def test_rejects_nonfinite_and_boolean_properties(self):
        for value in (float("nan"), float("inf"), True, 0, -1):
            with self.subTest(value=value):
                self.model["sections"]["COLUMN"]["E_Pa"] = value
                with self.assertRaises(ContractError):
                    validate_model(self.model)

    def test_rejects_disconnected_or_zero_length_geometry(self):
        self.model["nodes"]["5"] = [12, 4]
        with self.assertRaises(ContractError):
            validate_model(self.model)
        del self.model["nodes"]["5"]
        self.model["nodes"]["3"] = [0, 0]
        with self.assertRaises(ContractError):
            validate_model(self.model)

    def test_rejects_dangling_load_and_ambiguous_node_id(self):
        self.model["load_case"]["uniform"]["99"] = -1000
        with self.assertRaises(ContractError):
            validate_model(self.model)
        del self.model["load_case"]["uniform"]["99"]
        self.model["nodes"]["01"] = [1, 1]
        with self.assertRaises(ContractError):
            validate_model(self.model)


if __name__ == "__main__":
    unittest.main()
