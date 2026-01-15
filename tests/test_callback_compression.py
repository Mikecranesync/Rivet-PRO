"""
Unit tests for callback data compression module.

Tests cover:
1. Encoding/decoding correctness
2. 64-byte size limit compliance
3. Tree depth up to 10 levels
4. Collision detection
5. Performance requirements (< 1ms)
6. Edge cases and error handling
"""

import pytest
import time
from rivet_pro.troubleshooting.callback import (
    encode_callback,
    decode_callback,
    CallbackData,
    _encode_base62,
    _decode_base62,
    _hash_node_id,
    benchmark_encoding,
)


class TestBase62Encoding:
    """Test base62 integer encoding"""

    def test_encode_zero(self):
        assert _encode_base62(0) == '0'

    def test_encode_single_digit(self):
        assert _encode_base62(5) == '5'
        assert _encode_base62(9) == '9'

    def test_encode_letters(self):
        assert _encode_base62(10) == 'A'
        assert _encode_base62(35) == 'Z'
        assert _encode_base62(36) == 'a'
        assert _encode_base62(61) == 'z'

    def test_encode_multi_digit(self):
        assert _encode_base62(62) == '10'
        assert _encode_base62(123) == '1z'
        assert _encode_base62(999999) == '4C91'

    def test_roundtrip(self):
        """Test encode -> decode returns original"""
        for num in [0, 1, 10, 62, 123, 999, 999999, 2**20]:
            encoded = _encode_base62(num)
            decoded = _decode_base62(encoded)
            assert decoded == num, f"Failed roundtrip for {num}"


class TestNodeHashing:
    """Test node_id hashing"""

    def test_hash_consistency(self):
        """Same node_id always produces same hash"""
        node_id = "CheckMotorTemp"
        hash1 = _hash_node_id(node_id)
        hash2 = _hash_node_id(node_id)
        assert hash1 == hash2

    def test_hash_length(self):
        """Hash is always 4 characters"""
        test_ids = [
            "A",
            "RootNode",
            "CheckMotorTemp",
            "VerifyPowerSupply_Step1_Phase2_SubCheck_VeryLongNodeIdentifier",
        ]
        for node_id in test_ids:
            hash_val = _hash_node_id(node_id)
            assert len(hash_val) == 4, f"Hash length mismatch for {node_id}"

    def test_hash_uniqueness(self):
        """Different node_ids produce different hashes (probabilistic)"""
        node_ids = [
            "RootNode",
            "CheckMotorTemp",
            "VerifyPowerSupply",
            "InspectBearings",
            "TestVibration",
        ]
        hashes = [_hash_node_id(node_id) for node_id in node_ids]

        # All hashes should be unique (collision rate is ~1/65536)
        assert len(hashes) == len(set(hashes)), "Hash collision detected"


class TestCallbackEncoding:
    """Test callback data encoding"""

    def test_simple_encode(self):
        """Test basic encoding"""
        encoded = encode_callback(1, "RootNode", "navigate")
        assert encoded.startswith('ts:')
        assert len(encoded) < 64

    def test_large_tree_id(self):
        """Test large tree_id values"""
        encoded = encode_callback(999999, "TestNode", "select")
        assert len(encoded) < 64

    def test_long_node_id(self):
        """Test long node_id (should be hashed)"""
        long_node = "VerifyPowerSupply_Step1_Phase2_SubCheck_VeryLongNodeIdentifier"
        encoded = encode_callback(123, long_node, "back")
        assert len(encoded) < 64
        assert long_node not in encoded  # Should be hashed, not included directly

    def test_all_actions(self):
        """Test all action types"""
        actions = ['navigate', 'select', 'back', 'help', 'refresh', 'export']
        for action in actions:
            encoded = encode_callback(1, "TestNode", action)
            assert len(encoded) < 64

    def test_size_limit_compliance(self):
        """Test that encoded data never exceeds 64 bytes"""
        test_cases = [
            (0, "A", "navigate"),
            (1, "RootNode", "select"),
            (999999, "VeryLongNodeIdentifier" * 10, "back"),
            (2**20, "Node", "help"),
        ]

        for tree_id, node_id, action in test_cases:
            encoded = encode_callback(tree_id, node_id, action)
            assert len(encoded) <= 64, f"Encoded data exceeds 64 bytes: {len(encoded)}"

    def test_invalid_tree_id(self):
        """Test negative tree_id raises error"""
        with pytest.raises(ValueError, match="tree_id must be non-negative"):
            encode_callback(-1, "Node", "navigate")

    def test_invalid_node_id(self):
        """Test empty node_id raises error"""
        with pytest.raises(ValueError, match="node_id must be non-empty"):
            encode_callback(1, "", "navigate")

    def test_invalid_action(self):
        """Test invalid action raises error"""
        with pytest.raises(ValueError, match="action must be one of"):
            encode_callback(1, "Node", "invalid_action")


class TestCallbackDecoding:
    """Test callback data decoding"""

    def test_simple_decode(self):
        """Test basic decoding"""
        encoded = encode_callback(1, "RootNode", "navigate")
        decoded = decode_callback(encoded)

        assert isinstance(decoded, CallbackData)
        assert decoded.tree_id == 1
        assert decoded.node_id == "RootNode"
        assert decoded.action == "navigate"

    def test_roundtrip(self):
        """Test encode -> decode returns original data"""
        test_cases = [
            (1, "RootNode", "navigate"),
            (123, "CheckMotorTemp", "select"),
            (999999, "VerifyPowerSupply", "back"),
            (42, "InspectBearings", "help"),
        ]

        for tree_id, node_id, action in test_cases:
            encoded = encode_callback(tree_id, node_id, action)
            decoded = decode_callback(encoded)

            assert decoded.tree_id == tree_id
            assert decoded.node_id == node_id
            assert decoded.action == action

    def test_invalid_prefix(self):
        """Test invalid prefix raises error"""
        with pytest.raises(ValueError, match="Invalid callback data prefix"):
            decode_callback("invalid:1:abcd:n")

    def test_invalid_format(self):
        """Test malformed data raises error"""
        with pytest.raises(ValueError, match="Expected 4 parts"):
            decode_callback("ts:1:abcd")  # Missing action

    def test_invalid_action_code(self):
        """Test unknown action code raises error"""
        with pytest.raises(ValueError, match="Unknown action code"):
            decode_callback("ts:1:abcd:z")


class TestTreeDepth:
    """Test support for deep trees (up to 10 levels)"""

    def test_level_1_nodes(self):
        """Test root level (level 1)"""
        encoded = encode_callback(1, "L1_Root", "navigate")
        decoded = decode_callback(encoded)
        assert decoded.tree_id == 1
        assert len(encoded) < 64

    def test_level_5_nodes(self):
        """Test mid-depth nodes (level 5)"""
        node_id = "L1.L2.L3.L4.L5_MidDepthNode"
        encoded = encode_callback(1, node_id, "select")
        decoded = decode_callback(encoded)
        assert decoded.node_id == node_id
        assert len(encoded) < 64

    def test_level_10_nodes(self):
        """Test maximum depth (level 10)"""
        node_id = "L1.L2.L3.L4.L5.L6.L7.L8.L9.L10_DeepNode"
        encoded = encode_callback(1, node_id, "back")
        decoded = decode_callback(encoded)
        assert decoded.node_id == node_id
        assert len(encoded) < 64

    def test_multiple_trees(self):
        """Test multiple independent trees"""
        trees = []
        for tree_id in range(1, 11):
            for level in range(1, 11):
                node_id = f"Tree{tree_id}_Level{level}_Node"
                encoded = encode_callback(tree_id, node_id, "navigate")
                decoded = decode_callback(encoded)
                assert decoded.tree_id == tree_id
                assert decoded.node_id == node_id
                assert len(encoded) < 64
                trees.append(encoded)

        # All encodings should be unique
        assert len(trees) == len(set(trees))


class TestPerformance:
    """Test performance requirements (< 1ms per operation)"""

    def test_encode_performance(self):
        """Encoding should take < 1ms"""
        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            encode_callback(123, "CheckMotorTemp", "navigate")

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        assert avg_time_ms < 1.0, f"Encoding took {avg_time_ms:.3f}ms (> 1ms limit)"

    def test_decode_performance(self):
        """Decoding should take < 1ms"""
        encoded = encode_callback(123, "CheckMotorTemp", "navigate")

        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            decode_callback(encoded)

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        assert avg_time_ms < 1.0, f"Decoding took {avg_time_ms:.3f}ms (> 1ms limit)"

    def test_roundtrip_performance(self):
        """Full encode -> decode should take < 1ms"""
        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            encoded = encode_callback(123, "CheckMotorTemp", "navigate")
            decode_callback(encoded)

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        assert avg_time_ms < 1.0, f"Roundtrip took {avg_time_ms:.3f}ms (> 1ms limit)"

    def test_benchmark_function(self):
        """Test benchmark utility function"""
        results = benchmark_encoding(iterations=100)

        assert 'avg_encode_us' in results
        assert 'avg_decode_us' in results

        # Should be well under 1ms (1000 μs)
        assert results['avg_encode_us'] < 1000
        assert results['avg_decode_us'] < 1000


class TestCollisionResistance:
    """Test collision detection and handling"""

    def test_no_collisions_common_names(self):
        """Test common equipment node names don't collide"""
        node_ids = [
            "RootNode",
            "CheckMotor",
            "CheckMotorTemp",
            "CheckMotorVibration",
            "CheckPump",
            "CheckPumpPressure",
            "CheckPumpFlow",
            "InspectBearings",
            "InspectSeals",
            "TestVibration",
        ]

        hashes = {}
        for node_id in node_ids:
            hash_val = _hash_node_id(node_id)
            if hash_val in hashes:
                pytest.fail(
                    f"Hash collision: '{node_id}' and '{hashes[hash_val]}' "
                    f"both hash to {hash_val}"
                )
            hashes[hash_val] = node_id

    def test_similar_names_different_hashes(self):
        """Test similar names produce different hashes"""
        similar_nodes = [
            "CheckMotor",
            "CheckMotors",
            "CheckMotor1",
            "CheckMotor2",
            "checkmotor",  # Different case
        ]

        hashes = [_hash_node_id(node) for node in similar_nodes]
        assert len(hashes) == len(set(hashes)), "Similar names produced same hash"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_tree_id(self):
        """Test tree_id = 0"""
        encoded = encode_callback(0, "Node", "navigate")
        decoded = decode_callback(encoded)
        assert decoded.tree_id == 0

    def test_single_char_node_id(self):
        """Test single character node_id"""
        encoded = encode_callback(1, "A", "select")
        decoded = decode_callback(encoded)
        assert decoded.node_id == "A"

    def test_unicode_node_id(self):
        """Test unicode characters in node_id"""
        encoded = encode_callback(1, "节点_🔧", "navigate")
        decoded = decode_callback(encoded)
        assert decoded.node_id == "节点_🔧"

    def test_special_chars_node_id(self):
        """Test special characters in node_id"""
        node_id = "Node-With_Special.Chars!@#$%"
        encoded = encode_callback(1, node_id, "back")
        decoded = decode_callback(encoded)
        assert decoded.node_id == node_id

    def test_max_tree_id(self):
        """Test very large tree_id"""
        large_id = 2**30  # ~1 billion
        encoded = encode_callback(large_id, "Node", "help")
        decoded = decode_callback(encoded)
        assert decoded.tree_id == large_id
        assert len(encoded) < 64


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
