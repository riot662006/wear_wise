"""
Unit tests for style scoring system.
Tests each subscore and integration scenarios.
"""

import unittest
from typing import Any

from scoring import (
    score_outfit,
    load_config,
    OutfitFeatures,
)
from scoring.scorer import (
    score_color_harmony,
    score_pattern_balance,
    score_texture_mix,
    score_highlight_principle,
    score_proportion,
    score_repetition,
)
from scoring.color_distance import delta_e_00


class TestColorDistance(unittest.TestCase):
    """Test CIEDE2000 color distance calculation."""
    
    def test_same_color(self):
        """Same color should have distance 0."""
        lab = (50.0, 0.0, 0.0)
        d = delta_e_00(lab, lab)
        self.assertAlmostEqual(d, 0.0, places=1)
    
    def test_different_colors(self):
        """Different colors should have positive distance."""
        lab1 = (50.0, 0.0, 0.0)
        lab2 = (60.0, 10.0, 10.0)
        d = delta_e_00(lab1, lab2)
        self.assertGreater(d, 0.0)
        self.assertLess(d, 100.0)  # reasonable upper bound


class TestColorHarmony(unittest.TestCase):
    """Test Color Harmony subscore."""
    
    def setUp(self):
        self.cfg = load_config()
    
    def test_perfect_50_30_20(self):
        """Exact 50/30/20 ratio should score high."""
        clusters = [
            {"lab": (60.0, -5.0, -7.0), "pct": 0.50},
            {"lab": (48.0, 2.0, 4.0), "pct": 0.30},
            {"lab": (70.0, -6.0, -10.0), "pct": 0.20},
        ]
        C, _ = score_color_harmony(clusters, self.cfg)
        self.assertGreater(C, 0.7)  # Should be high
    
    def test_off_ratio(self):
        """70/20/10 ratio should score lower."""
        clusters = [
            {"lab": (60.0, -5.0, -7.0), "pct": 0.70},
            {"lab": (48.0, 2.0, 4.0), "pct": 0.20},
            {"lab": (70.0, -6.0, -10.0), "pct": 0.10},
        ]
        C, _ = score_color_harmony(clusters, self.cfg)
        self.assertLess(C, 0.8)  # Should be lower than perfect
    
    def test_deterministic(self):
        """Same input should produce same output."""
        clusters = [
            {"lab": (60.0, -5.0, -7.0), "pct": 0.50},
            {"lab": (48.0, 2.0, 4.0), "pct": 0.30},
            {"lab": (70.0, -6.0, -10.0), "pct": 0.20},
        ]
        C1, _ = score_color_harmony(clusters, self.cfg)
        C2, _ = score_color_harmony(clusters, self.cfg)
        self.assertEqual(C1, C2)


class TestPatternBalance(unittest.TestCase):
    """Test Pattern Balance subscore."""
    
    def setUp(self):
        self.cfg = load_config()
    
    def test_one_strong_pattern(self):
        """One strong pattern should score 1.0."""
        garments = [
            {"id": "g1", "type": "top", "patternType": "plaid", "patternStrength": 0.72, "material": "cotton", "colorLAB": (60, -5, -7), "areaPct": 0.3, "glossIndex": 0.1},
            {"id": "g2", "type": "bottom", "patternType": "none", "patternStrength": 0.0, "material": "denim", "colorLAB": (50, 0, 0), "areaPct": 0.4, "glossIndex": 0.05},
        ]
        P, _ = score_pattern_balance(garments, self.cfg)
        self.assertEqual(P, 1.0)
    
    def test_two_strong_patterns(self):
        """Two strong patterns should score lower."""
        garments = [
            {"id": "g1", "type": "top", "patternType": "plaid", "patternStrength": 0.72, "material": "cotton", "colorLAB": (60, -5, -7), "areaPct": 0.3, "glossIndex": 0.1},
            {"id": "g2", "type": "bottom", "patternType": "stripe", "patternStrength": 0.65, "material": "denim", "colorLAB": (50, 0, 0), "areaPct": 0.4, "glossIndex": 0.05},
        ]
        P, _ = score_pattern_balance(garments, self.cfg)
        self.assertLess(P, 1.0)
        self.assertGreaterEqual(P, 0.0)
    
    def test_no_patterns(self):
        """No patterns should score 0.7."""
        garments = [
            {"id": "g1", "type": "top", "patternType": "none", "patternStrength": 0.0, "material": "cotton", "colorLAB": (60, -5, -7), "areaPct": 0.3, "glossIndex": 0.1},
            {"id": "g2", "type": "bottom", "patternType": "none", "patternStrength": 0.0, "material": "denim", "colorLAB": (50, 0, 0), "areaPct": 0.4, "glossIndex": 0.05},
        ]
        P, _ = score_pattern_balance(garments, self.cfg)
        self.assertEqual(P, 0.7)


class TestTextureMix(unittest.TestCase):
    """Test Texture Mix subscore."""
    
    def setUp(self):
        self.cfg = load_config()
    
    def test_ideal_materials(self):
        """2-3 materials should score high."""
        garments = [
            {"id": "g1", "type": "top", "material": "cotton", "patternType": "none", "patternStrength": 0.0, "colorLAB": (60, -5, -7), "areaPct": 0.3, "glossIndex": 0.1},
            {"id": "g2", "type": "bottom", "material": "denim", "patternType": "none", "patternStrength": 0.0, "colorLAB": (50, 0, 0), "areaPct": 0.4, "glossIndex": 0.05},
        ]
        T, _ = score_texture_mix(garments, self.cfg)
        self.assertGreater(T, 0.7)
    
    def test_gloss_bonus(self):
        """Exactly one glossy piece should get bonus."""
        garments = [
            {"id": "g1", "type": "top", "material": "cotton", "patternType": "none", "patternStrength": 0.0, "colorLAB": (60, -5, -7), "areaPct": 0.3, "glossIndex": 0.1},
            {"id": "g2", "type": "accessory", "material": "leather", "patternType": "none", "patternStrength": 0.0, "colorLAB": (50, 0, 0), "areaPct": 0.1, "glossIndex": 0.8},
        ]
        T, _ = score_texture_mix(garments, self.cfg)
        self.assertGreaterEqual(T, 0.8)  # Should have bonus


class TestHighlightPrinciple(unittest.TestCase):
    """Test Highlight Principle subscore."""
    
    def setUp(self):
        self.cfg = load_config()
    
    def test_one_highlight(self):
        """Exactly one domain z≥1.0 should score 1.0."""
        domain_z = {"skin": 0.2, "hue": 1.4, "texture": 0.5, "pattern": 0.1}
        H, _ = score_highlight_principle(domain_z, self.cfg)
        self.assertEqual(H, 1.0)
    
    def test_two_highlights(self):
        """Two highlights should score 0.75."""
        domain_z = {"skin": 0.2, "hue": 1.4, "texture": 1.2, "pattern": 0.1}
        H, _ = score_highlight_principle(domain_z, self.cfg)
        self.assertEqual(H, 0.75)
    
    def test_no_highlights(self):
        """No highlights should score 0.6."""
        domain_z = {"skin": 0.2, "hue": 0.5, "texture": 0.3, "pattern": 0.1}
        H, _ = score_highlight_principle(domain_z, self.cfg)
        self.assertEqual(H, 0.6)


class TestProportion(unittest.TestCase):
    """Test Proportion subscore."""
    
    def setUp(self):
        self.cfg = load_config()
    
    def test_ideal_ratio(self):
        """0.33 top ratio should score high."""
        thirds = {"top": 0.33, "mid": 0.34, "bottom": 0.33}
        B, _ = score_proportion(thirds, None, self.cfg)
        self.assertGreater(B, 0.8)
    
    def test_extreme_ratio(self):
        """Extreme ratios should score lower."""
        thirds = {"top": 0.8, "mid": 0.1, "bottom": 0.1}
        B, _ = score_proportion(thirds, None, self.cfg)
        self.assertLess(B, 0.5)
    
    def test_with_waist_neck(self):
        """Waist/neck echo should affect score."""
        thirds = {"top": 0.33, "mid": 0.34, "bottom": 0.33}
        body = {"waist": 80.0, "neck": 40.0}  # 2.0 ratio (should be 0.2)
        B, _ = score_proportion(thirds, body, self.cfg)
        # Should still be reasonable but not perfect
        self.assertGreater(B, 0.0)
        self.assertLessEqual(B, 1.0)


class TestRepetition(unittest.TestCase):
    """Test Repetition/Echo subscore."""
    
    def test_good_echo(self):
        """Accessory within ΔE≤10 should score 1.0."""
        garments = [
            {"id": "g1", "type": "top", "material": "cotton", "patternType": "none", "patternStrength": 0.0, "colorLAB": (60, -5, -7), "areaPct": 0.3, "glossIndex": 0.1},
            {"id": "g2", "type": "accessory", "material": "leather", "patternType": "none", "patternStrength": 0.0, "colorLAB": (60, -5, -7), "areaPct": 0.1, "glossIndex": 0.8},  # Same color
        ]
        clusters = [
            {"lab": (60, -5, -7), "pct": 0.52},
            {"lab": (48, 2, 4), "pct": 0.30},
        ]
        R, _ = score_repetition(garments, clusters)
        self.assertEqual(R, 1.0)
    
    def test_no_accessories(self):
        """No accessories should score 0.3."""
        garments = [
            {"id": "g1", "type": "top", "material": "cotton", "patternType": "none", "patternStrength": 0.0, "colorLAB": (60, -5, -7), "areaPct": 0.3, "glossIndex": 0.1},
            {"id": "g2", "type": "bottom", "material": "denim", "patternType": "none", "patternStrength": 0.0, "colorLAB": (50, 0, 0), "areaPct": 0.4, "glossIndex": 0.05},
        ]
        clusters = [
            {"lab": (60, -5, -7), "pct": 0.52},
            {"lab": (48, 2, 4), "pct": 0.30},
        ]
        R, _ = score_repetition(garments, clusters)
        self.assertEqual(R, 0.3)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete scoring."""
    
    def setUp(self):
        self.cfg = load_config()
    
    def test_example_from_spec(self):
        """Test the example outfit from the spec."""
        features: OutfitFeatures = {
            "outfitId": "abc123",
            "garments": [
                {
                    "id": "top1",
                    "type": "top",
                    "areaPct": 0.31,
                    "colorLAB": (62, -4, -8),
                    "material": "cotton",
                    "patternType": "plaid",
                    "patternStrength": 0.72,
                    "glossIndex": 0.1,
                },
                {
                    "id": "pant1",
                    "type": "bottom",
                    "areaPct": 0.41,
                    "colorLAB": (50, 0, 0),
                    "material": "denim",
                    "patternType": "none",
                    "patternStrength": 0.0,
                    "glossIndex": 0.05,
                },
                {
                    "id": "shoe1",
                    "type": "accessory",
                    "areaPct": 0.06,
                    "colorLAB": (60, -5, -7),
                    "material": "leather",
                    "patternType": "none",
                    "patternStrength": 0.0,
                    "glossIndex": 0.8,
                },
            ],
            "colorClusters": [
                {"lab": (60, -5, -7), "pct": 0.52},
                {"lab": (48, 2, 4), "pct": 0.30},
                {"lab": (70, -6, -10), "pct": 0.18},
            ],
            "thirdsArea": {"top": 0.35, "mid": 0.30, "bottom": 0.35},
            "domainZ": {"skin": 0.2, "hue": 1.4, "texture": 0.5, "pattern": 0.1},
            "extractionVersion": "segm-1.2.0-kmeans-3",
            "body": None,
        }
        
        result = score_outfit(features, self.cfg)
        
        # Validate structure
        self.assertIn("version", result)
        self.assertIn("styleScore", result)
        self.assertIn("subscores", result)
        self.assertIn("explanations", result)
        self.assertIn("debug", result)
        
        # Validate score range
        self.assertGreaterEqual(result["styleScore"], 0.0)
        self.assertLessEqual(result["styleScore"], 100.0)
        
        # Validate subscores
        subscores = result["subscores"]
        for key in ["colorHarmony", "patternBalance", "textureMix", "highlightPrinciple", "proportion", "repetition"]:
            self.assertIn(key, subscores)
            self.assertGreaterEqual(subscores[key], 0.0)
            self.assertLessEqual(subscores[key], 1.0)
        
        # Should have explanations
        self.assertGreater(len(result["explanations"]), 0)
    
    def test_deterministic(self):
        """Same input should produce same output."""
        features: OutfitFeatures = {
            "outfitId": "test",
            "garments": [
                {
                    "id": "g1",
                    "type": "top",
                    "areaPct": 0.3,
                    "colorLAB": (60, -5, -7),
                    "material": "cotton",
                    "patternType": "none",
                    "patternStrength": 0.0,
                    "glossIndex": 0.1,
                },
            ],
            "colorClusters": [
                {"lab": (60, -5, -7), "pct": 1.0},
            ],
            "thirdsArea": {"top": 0.33, "mid": 0.34, "bottom": 0.33},
            "domainZ": {"skin": 0.2, "hue": 0.5, "texture": 0.3, "pattern": 0.1},
            "extractionVersion": "test-1.0",
            "body": None,
        }
        
        result1 = score_outfit(features, self.cfg)
        result2 = score_outfit(features, self.cfg)
        
        self.assertEqual(result1["styleScore"], result2["styleScore"])
        for key in result1["subscores"]:
            self.assertEqual(result1["subscores"][key], result2["subscores"][key])


if __name__ == "__main__":
    unittest.main()

