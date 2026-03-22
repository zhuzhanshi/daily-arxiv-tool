"""测试分类规则。"""

import sys
from pathlib import Path

# 同目录下直接 import
from classify import classify_paper
from config import Config


def test_classify_vlm():
    assert classify_paper(
        "Visual Instruction Tuning for Multimodal LLMs",
        "We propose a vision-language model that combines visual reasoning with instruction tuning.",
    ) == "multimodal_vlm"


def test_classify_llm_reasoning():
    assert classify_paper(
        "Thinking Deeper with Chain-of-Thought",
        "We study mathematical reasoning through chain-of-thought prompting.",
    ) == "llm_reasoning"


def test_classify_image_generation():
    assert classify_paper(
        "Fast Diffusion Models",
        "We propose a new diffusion model for text-to-image generation.",
    ) == "image_generation"


def test_classify_3d_vision():
    assert classify_paper(
        "GS-SLAM: Dense SLAM with Gaussian Splatting",
        "We present a real-time SLAM system using 3d gaussian splatting for 3d reconstruction.",
    ) == "3d_vision"


def test_classify_robotics():
    assert classify_paper(
        "RoboGrasp: Dexterous Manipulation",
        "We study embodied robot grasping with sim-to-real transfer.",
    ) == "robotics"


def test_classify_llm_agent():
    assert classify_paper(
        "ToolAgent: LLM with Tool Use",
        "We propose an llm agent framework for tool use and function calling.",
    ) == "llm_agent"


def test_classify_custom_domain():
    cfg = Config()
    from config import DomainDef
    cfg.domains["quantum"] = DomainDef(
        name="量子计算", emoji="⚛️",
        keywords=["quantum comput", "qubit"],
        priority=1,
    )
    assert classify_paper(
        "Quantum Computing for ML",
        "We study quantum computing algorithms for machine learning.",
        cfg,
    ) == "quantum"


def test_classify_fallback():
    assert classify_paper(
        "Some Random Paper",
        "This paper studies general network optimization.",
    ) == "others"


if __name__ == "__main__":
    test_classify_vlm()
    test_classify_llm_reasoning()
    test_classify_image_generation()
    test_classify_3d_vision()
    test_classify_robotics()
    test_classify_llm_agent()
    test_classify_custom_domain()
    test_classify_fallback()
    print("✅ All tests passed")
