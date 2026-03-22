"""论文领域分类规则 — 28 个 AI 子领域的关键词匹配。

支持两种模式:
1. 内置规则（默认）: 覆盖 CV/NLP/LLM/多模态等 28 个领域
2. 用户自定义: 通过 config.yaml 的 domains 字段覆盖或新增
"""

from config import Config, DomainDef

# --------------------------------------------------------------------------
# 内置分类规则 — (keywords, domain_id)，按优先级排序
# --------------------------------------------------------------------------
BUILTIN_RULES: list[tuple[list[str], str]] = [
    # ══ 视觉 / 医学 / 驾驶 ══
    (["medical", "clinical", "patholog", "radiology", "x-ray", "mri", "surgical",
      "retina", "cancer", "tumor", "lesion", "ultrasound", "endoscop", "histopath",
      "ophthal", "brain mri", "echocardiog", "chest x-ray", "ct scan", "fundus",
      "drug discovery", "molecule generat", "protein", "genomic", "biomedical"],
     "medical_imaging"),
    (["autonomous driv", "self-driving", "lidar", "bev ", "occupancy predict",
      "lane detect", "traffic", "vehicle detect", "driving scene", "pedestrian",
      "trajectory predict", "autonomous vehicle"],
     "autonomous_driving"),
    (["3d gaussian", "gaussian splat", "nerf", "neural radiance", "3d reconstruct",
      "3d generation", "mesh ", "point cloud", "3d object", "slam",
      "structure from motion", "sfm", "stereo match", "depth estimat",
      "monocular depth", "3d scene", "novel view", "view synthesis",
      "3d aware", "3d-aware", "voxel", "3d detect", "3d perception"],
     "3d_vision"),
    (["segmentat", "panoptic", "semantic seg", "instance seg", "salient object",
      "camouflage", "referring seg", "open-vocabulary seg", "interactive seg"],
     "segmentation"),
    (["object detect", "detector ", "yolo", "detr", "anchor", "bounding box",
      "few-shot detect"],
     "object_detection"),
    (["diffusion model", "text-to-image", "image generation", "image synthesis",
      "generative model", "inpainting", "image editing", "style transfer",
      "text-to-3d", "image-to-image", "denoising score", "flow matching",
      "score-based", "rectified flow"],
     "image_generation"),
    (["video generation", "video synthesis", "video editing", "video understand",
      "video question", "temporal ground", "action recogn", "action detect",
      "optical flow", "video object", "tracking", "frame interpolat",
      "video caption", "video grounding", "video language", "video-language"],
     "video_understanding"),
    (["image restor", "deblur", "denois", "derain", "dehaze", "low-light",
      "image enhance", "super-resol"],
     "image_restoration"),
    (["remote sensing", "aerial", "satellite", "geo-spatial", "hyperspectral"],
     "remote_sensing"),
    (["face ", "person re-id", "pose estimat", "human pose", "hand ",
      "body ", "avatar", "gesture", "skeleton", "gait", "motion capture",
      "human mesh", "human motion", "garment"],
     "human_understanding"),
    (["adversarial attack", "backdoor", "watermark", "privacy",
      "fairness", "deepfake", "forgery detect"],
     "ai_safety"),

    # ══ RL / 时序 / 语音 / 图 / 机器人 / 推荐 ══
    (["reinforcement learn", "multi-agent reinforcement", "policy gradient",
      "q-learning", "actor-critic", "markov decision", "reward shaping",
      "multi-arm bandit", "bandit algorithm", "contextual bandit",
      "offline reinforcement", "online reinforcement", "imitation learn",
      "inverse reinforcement"],
     "reinforcement_learning"),
    (["time series", "time-series", "forecasting", "temporal pattern",
      "sequential data", "anomaly detection in time"],
     "time_series"),
    (["speech recogn", "speech synth", "text-to-speech", "audio",
      "speaker ", "voice ", "acoustic", "music generat", "music ",
      "sound ", "asr ", "tts "],
     "audio_speech"),
    (["graph neural", "graph transform", "graph convolu", "node classif",
      "link predict", "knowledge graph", "heterogeneous graph",
      "graph generation", "molecular graph", "message passing"],
     "graph_learning"),
    (["robot", "embodied", "manipulat", "grasp", "navigation",
      "locomotion", "dexterous", "sim-to-real"],
     "robotics"),
    (["recommend", "collaborative filter", "click-through rate",
      "user preference", "item recommend", "sequential recommend"],
     "recommender"),

    # ══ VLM / 多模态 ══
    (["vision-language", "vlm", "multimodal", "multi-modal", "visual question",
      "image caption", "visual grounding", "mllm", "visual reasoning",
      "vision language action", "vla ", "vision-language-action",
      "visual instruction", "visual prompt"],
     "multimodal_vlm"),

    # ══ 模型压缩 ══
    (["pruning", "quantiz", "distill", "compress", "lightweight",
      "parameter-efficient", "lora", "adapter", "token compress",
      "token merg", "efficient infer", "model effici",
      "knowledge distill"],
     "model_compression"),

    # ══ 自监督 ══
    (["self-supervis", "contrastive learn", "masked auto",
      "representation learn", "foundation model"],
     "self_supervised"),

    # ══ LLM 子领域 ══
    (["chain-of-thought", "chain of thought", "mathematical reason",
      "logical reason", "test-time scal", "test time scal",
      "step-by-step reason", "reasoning model", "self-consistency",
      "multi-step reason", "tree of thought", "reasoning chain",
      "cot ", "process reward", "verifier", "thinking model"],
     "llm_reasoning"),
    (["llm agent", "tool use", "tool-augment", "tool augment",
      "gui agent", "agentic", "web agent", "code agent",
      "tool select", "tool call", "react framework",
      "function calling", "api call"],
     "llm_agent"),
    (["rlhf", "reinforcement learning from human", "dpo ",
      "direct preference", "grpo", "reward model", "preference optim",
      "instruction tun", "human feedback", "steerabil",
      "preference learn", "value alignment", "safety alignment",
      "red teaming", "jailbreak"],
     "llm_alignment"),
    (["speculative decod", "kv cache", "long context", "long-context",
      "context window", "flash attention", "mixture of expert",
      " moe ", "sparse attention", "token effici",
      "attention effici", "context length", "inference effici",
      "serving", "batched infer", "model parallel"],
     "llm_efficiency"),
    (["named entity", " ner ", "sentiment", "text classif",
      "information extract", "question answer", "reading comprehens",
      "relation extract", "event extract"],
     "nlp_understanding"),
    (["text generat", "summariz", "machine translat", "neural machine",
      "dialogue system", "code generat", "program synth",
      "controllable generat", "data-to-text"],
     "nlp_generation"),

    # ══ LLM 兜底 ══
    (["large language model", "llm", "prompt", "in-context learn",
      "language model", "tokeniz", "pretrain", "scaling law",
      " nlp ", "natural language process", "transformer"],
     "llm_nlp"),
]

# 负面规则 — 某些关键词同时出现时应跳过该分类
BUILTIN_NEGATIVE_RULES: dict[str, list[str]] = {
    "llm_agent": [
        "reinforcement learn", "multi-agent reinforcement", "policy gradient",
        "q-learning", "actor-critic", "markov decision",
    ],
    "reinforcement_learning": [
        "llm agent", "gui agent", "web agent", "code agent",
        "rlhf", "direct preference", "grpo", "human feedback",
    ],
    "llm_alignment": [
        "representational alignment", "feature alignment", "domain adaptation",
        "image alignment", "sequence alignment",
    ],
}

# 内置领域元信息
BUILTIN_DOMAINS: dict[str, DomainDef] = {
    "medical_imaging":      DomainDef("医学影像", "🏥", [], 1),
    "autonomous_driving":   DomainDef("自动驾驶", "🚗", [], 2),
    "3d_vision":            DomainDef("3D视觉", "🧊", [], 3),
    "segmentation":         DomainDef("图像分割", "🎯", [], 4),
    "object_detection":     DomainDef("目标检测", "🔍", [], 5),
    "image_generation":     DomainDef("图像生成", "🎨", [], 6),
    "video_understanding":  DomainDef("视频理解", "🎬", [], 7),
    "image_restoration":    DomainDef("图像修复", "🖼️", [], 8),
    "remote_sensing":       DomainDef("遥感", "🛰️", [], 9),
    "human_understanding":  DomainDef("人体理解", "👤", [], 10),
    "ai_safety":            DomainDef("AI安全", "🛡️", [], 11),
    "reinforcement_learning": DomainDef("强化学习", "🎮", [], 12),
    "time_series":          DomainDef("时间序列", "📈", [], 13),
    "audio_speech":         DomainDef("语音音频", "🔊", [], 14),
    "graph_learning":       DomainDef("图学习", "🕸️", [], 15),
    "robotics":             DomainDef("机器人", "🤖", [], 16),
    "recommender":          DomainDef("推荐系统", "📋", [], 17),
    "multimodal_vlm":       DomainDef("多模态/VLM", "🧩", [], 18),
    "model_compression":    DomainDef("模型压缩", "📦", [], 19),
    "self_supervised":      DomainDef("自监督学习", "🔄", [], 20),
    "llm_reasoning":        DomainDef("LLM推理", "🧠", [], 21),
    "llm_agent":            DomainDef("LLM Agent", "🦾", [], 22),
    "llm_alignment":        DomainDef("LLM对齐", "⚖️", [], 23),
    "llm_efficiency":       DomainDef("LLM效率", "⚡", [], 24),
    "nlp_understanding":    DomainDef("NLP理解", "📖", [], 25),
    "nlp_generation":       DomainDef("NLP生成", "✍️", [], 26),
    "llm_nlp":              DomainDef("LLM/NLP", "🗣️", [], 27),
    "others":               DomainDef("其他", "📄", [], 99),
}

# 领域展示排序
DOMAIN_ORDER = [
    "image_generation", "video_understanding", "3d_vision",
    "object_detection", "segmentation", "image_restoration",
    "autonomous_driving", "remote_sensing", "human_understanding",
    "medical_imaging",
    "multimodal_vlm", "llm_reasoning", "llm_agent", "llm_alignment",
    "llm_efficiency", "llm_nlp", "nlp_understanding", "nlp_generation",
    "model_compression", "self_supervised",
    "robotics", "reinforcement_learning", "graph_learning",
    "audio_speech", "time_series", "recommender", "ai_safety",
    "others",
]


def get_domain_name(domain_id: str, cfg: Config | None = None) -> str:
    """获取领域显示名称。"""
    if cfg and domain_id in cfg.domains:
        return cfg.domains[domain_id].name
    if domain_id in BUILTIN_DOMAINS:
        return BUILTIN_DOMAINS[domain_id].name
    return domain_id


def get_domain_emoji(domain_id: str, cfg: Config | None = None) -> str:
    """获取领域 Emoji。"""
    if cfg and domain_id in cfg.domains:
        return cfg.domains[domain_id].emoji
    if domain_id in BUILTIN_DOMAINS:
        return BUILTIN_DOMAINS[domain_id].emoji
    return "📄"


def domain_sort_key(domain_id: str) -> int:
    """领域排序权重。"""
    if domain_id in DOMAIN_ORDER:
        return DOMAIN_ORDER.index(domain_id)
    return len(DOMAIN_ORDER)


def classify_paper(title: str, abstract: str, cfg: Config | None = None) -> str:
    """根据标题和摘要分类论文到最匹配的领域。

    优先匹配用户自定义域（按 priority 排序），再匹配内置规则。
    """
    text = f"{title} {abstract}".lower()

    # 1. 用户自定义领域（按 priority 排序）
    if cfg and cfg.domains:
        custom_sorted = sorted(cfg.domains.items(), key=lambda x: x[1].priority)
        for domain_id, ddef in custom_sorted:
            if any(kw.lower() in text for kw in ddef.keywords):
                return domain_id

    # 2. 内置规则
    for keywords, domain_id in BUILTIN_RULES:
        if any(kw in text for kw in keywords):
            neg_keywords = BUILTIN_NEGATIVE_RULES.get(domain_id, [])
            if neg_keywords and any(nk in text for nk in neg_keywords):
                continue
            return domain_id

    return "others"
