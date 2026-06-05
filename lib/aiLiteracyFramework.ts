export const aiLiteracyFramework = [
  {
    code: "U",
    dimension: "理解AI（Understand）",
    secondaryDimensions: [
      "知道人工智能的基本概念（如机器学习、生成式AI等）",
      "理解AI基于数据进行训练和生成结果的基本机制",
      "知道AI输出具有不确定性，可能出现错误或“幻觉”",
      "能区分AI擅长与不擅长处理的任务类型"
    ]
  },
  {
    code: "A",
    dimension: "应用AI（Apply）",
    secondaryDimensions: [
      "能判断某一任务是否适合使用AI完成",
      "能清晰描述问题并与AI进行有效交互",
      "能通过调整提问或指令优化AI输出结果",
      "能对AI生成结果的准确性和合理性进行判断"
    ]
  },
  {
    code: "C",
    dimension: "创造AI（Create）",
    secondaryDimensions: [
      "能将真实问题转化为可由AI支持的问题形式",
      "能利用AI生成并比较多种解决方案",
      "能整合AI工具设计解决问题的流程或路径",
      "能基于AI对方案进行调整、改进并形成较完整的解决方案"
    ]
  },
  {
    code: "E",
    dimension: "AI伦理（Ethics）",
    secondaryDimensions: [
      "关注使用AI过程中的数据隐私与信息安全问题",
      "能识别AI可能带来的偏见或不公平现象",
      "在使用AI时遵循学术规范与诚信原则",
      "意识到AI使用中的责任归属与潜在风险"
    ]
  }
] as const;

export const aiLiteracyDimensions = aiLiteracyFramework.map((item) => item.dimension);

export const aiLiteracySecondaryDimensions = aiLiteracyFramework.flatMap(
  (item) => item.secondaryDimensions
);

export function getSecondaryDimensions(dimension: string) {
  return aiLiteracyFramework.find((item) => item.dimension === dimension)?.secondaryDimensions ?? [];
}

export function isValidDimensionPair(dimension?: string, secondaryDimension?: string) {
  return Boolean(
    dimension &&
      secondaryDimension &&
      getSecondaryDimensions(dimension).some((item) => item === secondaryDimension)
  );
}

export function formatFrameworkForPrompt() {
  return aiLiteracyFramework
    .map(
      (item) =>
        `${item.code}. ${item.dimension}\n${item.secondaryDimensions
          .map((secondaryDimension, index) => `${index + 1}. ${secondaryDimension}`)
          .join("\n")}`
    )
    .join("\n\n");
}

export function normalizeFrameworkSelection(
  dimension = "",
  secondaryDimension = "",
  context = ""
) {
  const currentDimension = aiLiteracyFramework.find((item) => item.dimension === dimension);
  if (currentDimension?.secondaryDimensions.some((item) => item === secondaryDimension)) {
    return { dimension, secondaryDimension };
  }

  const text = `${dimension} ${secondaryDimension} ${context}`;
  let normalizedDimension = currentDimension?.dimension;

  if (!normalizedDimension) {
    if (/伦理|隐私|安全|偏见|公平|诚信|版权|合规|责任|风险/.test(text)) {
      normalizedDimension = "AI伦理（Ethics）";
    } else if (/创造|建模|方案|流程|路径|整合|改进|真实问题/.test(text)) {
      normalizedDimension = "创造AI（Create）";
    } else if (/应用|工具|提示|提问|交互|任务|结果|核验|判断/.test(text)) {
      normalizedDimension = "应用AI（Apply）";
    } else {
      normalizedDimension = "理解AI（Understand）";
    }
  }

  const secondaries = getSecondaryDimensions(normalizedDimension);
  let normalizedSecondary = secondaries[0] ?? "";

  if (normalizedDimension === "理解AI（Understand）") {
    if (/数据|训练|生成机制/.test(text)) {
      normalizedSecondary = "理解AI基于数据进行训练和生成结果的基本机制";
    } else if (/不确定|错误|幻觉/.test(text)) {
      normalizedSecondary = "知道AI输出具有不确定性，可能出现错误或“幻觉”";
    } else if (/擅长|不擅长|任务类型/.test(text)) {
      normalizedSecondary = "能区分AI擅长与不擅长处理的任务类型";
    }
  }

  if (normalizedDimension === "应用AI（Apply）") {
    if (/适合|任务是否|任务/.test(text)) {
      normalizedSecondary = "能判断某一任务是否适合使用AI完成";
    } else if (/描述问题|交互/.test(text)) {
      normalizedSecondary = "能清晰描述问题并与AI进行有效交互";
    } else if (/提问|指令|提示|优化/.test(text)) {
      normalizedSecondary = "能通过调整提问或指令优化AI输出结果";
    } else if (/准确|合理|结果|核验|可靠/.test(text)) {
      normalizedSecondary = "能对AI生成结果的准确性和合理性进行判断";
    }
  }

  if (normalizedDimension === "创造AI（Create）") {
    if (/转化|真实问题|建模|问题形式/.test(text)) {
      normalizedSecondary = "能将真实问题转化为可由AI支持的问题形式";
    } else if (/多种|比较|解决方案/.test(text)) {
      normalizedSecondary = "能利用AI生成并比较多种解决方案";
    } else if (/整合|流程|路径/.test(text)) {
      normalizedSecondary = "能整合AI工具设计解决问题的流程或路径";
    } else if (/调整|改进|完整/.test(text)) {
      normalizedSecondary = "能基于AI对方案进行调整、改进并形成较完整的解决方案";
    }
  }

  if (normalizedDimension === "AI伦理（Ethics）") {
    if (/隐私|信息安全|数据/.test(text)) {
      normalizedSecondary = "关注使用AI过程中的数据隐私与信息安全问题";
    } else if (/偏见|公平|不公平/.test(text)) {
      normalizedSecondary = "能识别AI可能带来的偏见或不公平现象";
    } else if (/学术|诚信|版权|合规|规范/.test(text)) {
      normalizedSecondary = "在使用AI时遵循学术规范与诚信原则";
    } else if (/责任|风险/.test(text)) {
      normalizedSecondary = "意识到AI使用中的责任归属与潜在风险";
    }
  }

  return {
    dimension: normalizedDimension,
    secondaryDimension: normalizedSecondary
  };
}
