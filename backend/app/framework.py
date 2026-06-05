from typing import Dict, List
import re


UACE_FRAMEWORK = [
    {
        "code": "U",
        "dimension": "理解AI（Understand）",
        "secondaryDimensions": [
            "知道人工智能的基本概念（如机器学习、生成式AI等）",
            "理解AI基于数据进行训练和生成结果的基本机制",
            "知道AI输出具有不确定性，可能出现错误或“幻觉”",
            "能区分AI擅长与不擅长处理的任务类型",
        ],
    },
    {
        "code": "A",
        "dimension": "应用AI（Apply）",
        "secondaryDimensions": [
            "能判断某一任务是否适合使用AI完成",
            "能清晰描述问题并与AI进行有效交互",
            "能通过调整提问或指令优化AI输出结果",
            "能对AI生成结果的准确性和合理性进行判断",
        ],
    },
    {
        "code": "C",
        "dimension": "创造AI（Create）",
        "secondaryDimensions": [
            "能将真实问题转化为可由AI支持的问题形式",
            "能利用AI生成并比较多种解决方案",
            "能整合AI工具设计解决问题的流程或路径",
            "能基于AI对方案进行调整、改进并形成较完整的解决方案",
        ],
    },
    {
        "code": "E",
        "dimension": "AI伦理（Ethics）",
        "secondaryDimensions": [
            "关注使用AI过程中的数据隐私与信息安全问题",
            "能识别AI可能带来的偏见或不公平现象",
            "在使用AI时遵循学术规范与诚信原则",
            "意识到AI使用中的责任归属与潜在风险",
        ],
    },
]


DIMENSIONS = [item["dimension"] for item in UACE_FRAMEWORK]
SECONDARY_BY_DIMENSION: Dict[str, List[str]] = {
    item["dimension"]: item["secondaryDimensions"] for item in UACE_FRAMEWORK
}
ALL_SECONDARY_DIMENSIONS = [
    secondary for item in UACE_FRAMEWORK for secondary in item["secondaryDimensions"]
]


def get_secondary_dimensions(dimension: str) -> List[str]:
    return SECONDARY_BY_DIMENSION.get(dimension, [])


def is_valid_pair(dimension: str, secondary_dimension: str) -> bool:
    return secondary_dimension in get_secondary_dimensions(dimension)


def format_framework_for_prompt() -> str:
    blocks = []
    for item in UACE_FRAMEWORK:
        secondary_lines = "\n".join(
            f"{index + 1}. {secondary}"
            for index, secondary in enumerate(item["secondaryDimensions"])
        )
        blocks.append(f"{item['code']}. {item['dimension']}\n{secondary_lines}")
    return "\n\n".join(blocks)


def normalize_framework_selection(
    dimension: str = "",
    secondary_dimension: str = "",
    context: str = "",
) -> Dict[str, str]:
    if is_valid_pair(dimension, secondary_dimension):
        return {"dimension": dimension, "secondaryDimension": secondary_dimension}

    text = f"{dimension} {secondary_dimension} {context}"
    normalized_dimension = dimension if dimension in DIMENSIONS else ""

    if not normalized_dimension:
        if re.search(r"伦理|隐私|安全|偏见|公平|诚信|版权|合规|责任|风险", text):
            normalized_dimension = "AI伦理（Ethics）"
        elif re.search(r"创造|建模|方案|流程|路径|整合|改进|真实问题", text):
            normalized_dimension = "创造AI（Create）"
        elif re.search(r"应用|工具|提示|提问|交互|任务|结果|核验|判断", text):
            normalized_dimension = "应用AI（Apply）"
        else:
            normalized_dimension = "理解AI（Understand）"

    secondaries = get_secondary_dimensions(normalized_dimension)
    normalized_secondary = secondaries[0] if secondaries else ""

    if normalized_dimension == "理解AI（Understand）":
        if re.search(r"数据|训练|生成机制", text):
            normalized_secondary = "理解AI基于数据进行训练和生成结果的基本机制"
        elif re.search(r"不确定|错误|幻觉", text):
            normalized_secondary = "知道AI输出具有不确定性，可能出现错误或“幻觉”"
        elif re.search(r"擅长|不擅长|任务类型", text):
            normalized_secondary = "能区分AI擅长与不擅长处理的任务类型"

    if normalized_dimension == "应用AI（Apply）":
        if re.search(r"适合|任务是否|任务", text):
            normalized_secondary = "能判断某一任务是否适合使用AI完成"
        elif re.search(r"描述问题|交互", text):
            normalized_secondary = "能清晰描述问题并与AI进行有效交互"
        elif re.search(r"提问|指令|提示|优化", text):
            normalized_secondary = "能通过调整提问或指令优化AI输出结果"
        elif re.search(r"准确|合理|结果|核验|可靠", text):
            normalized_secondary = "能对AI生成结果的准确性和合理性进行判断"

    if normalized_dimension == "创造AI（Create）":
        if re.search(r"转化|真实问题|建模|问题形式", text):
            normalized_secondary = "能将真实问题转化为可由AI支持的问题形式"
        elif re.search(r"多种|比较|解决方案", text):
            normalized_secondary = "能利用AI生成并比较多种解决方案"
        elif re.search(r"整合|流程|路径", text):
            normalized_secondary = "能整合AI工具设计解决问题的流程或路径"
        elif re.search(r"调整|改进|完整", text):
            normalized_secondary = "能基于AI对方案进行调整、改进并形成较完整的解决方案"

    if normalized_dimension == "AI伦理（Ethics）":
        if re.search(r"隐私|信息安全|数据", text):
            normalized_secondary = "关注使用AI过程中的数据隐私与信息安全问题"
        elif re.search(r"偏见|公平|不公平", text):
            normalized_secondary = "能识别AI可能带来的偏见或不公平现象"
        elif re.search(r"学术|诚信|版权|合规|规范", text):
            normalized_secondary = "在使用AI时遵循学术规范与诚信原则"
        elif re.search(r"责任|风险", text):
            normalized_secondary = "意识到AI使用中的责任归属与潜在风险"

    return {"dimension": normalized_dimension, "secondaryDimension": normalized_secondary}
