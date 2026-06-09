# LLM4AD 通用数学建模进化算法

**版本**: v1.0  
**适用**: 所有MCM/ICM类型的数学建模竞赛问题  
**核心思想**: 不是搜索问题的答案，而是搜索**解决这个问题的最佳建模范式**

---

## 🎯 算法核心定位

### 传统数学建模流程
```
拿到问题 → 查文献 → 选一个模型 → 调参 → 写论文
          ↑ 这里是单点故障：模型选错了全错
```

### LLM4AD进化建模流程
```
拿到问题 → 定义建模基因空间 → 进化搜索1000种建模算法
            → 输出Pareto前沿算法族 → 用不同算法回答不同问题
          ↑ 这里是鲁棒的：模型不会选错，而是进化出最好的
```

---

## 🧬 第一步：通用八维建模基因空间

**任何数模问题都可以用这8个维度来编码其建模方法论。**

| 基因座 | 维度含义 | 典型等位基因（按问题类型填充）|
|--------|---------|-----------------------------|
| **1. dynamics** | 系统动力学保真度 | 静态方程 / ODE / PDE / 随机过程 / 基于Agent / 图神经网络 |
| **2. constraints** | 约束处理方式 | 硬截断 / 软惩罚 / 障碍函数 / 拉格朗日松弛 / 机会约束 |
| **3. objective_form** | 目标函数数学形式 | 线性加权 / 切比雪夫 / 指数效用 / 字典序 / 最小最大公平 / 前景理论 |
| **4. stakeholder_subset** | 利益相关方建模 | 核心3方 / 全面5方 / 公平优先 / 效率优先 / 风险优先 |
| **5. solver** | 优化求解器范式 | 梯度下降 / LP / QP / GA / PSO / MPC / 贝叶斯优化 / ADMM / 内点法 |
| **6. temporal_arch** | 时间架构设计 | 静态 / 单步 / 滚动时域 / 多尺度 / 事件触发 / 连续时间 |
| **7. robustness** | 鲁棒性范式 | 确定性 / 最坏情形 / 随机期望 / CVaR / 分布鲁棒 / 对抗鲁棒 |
| **8. coupling** | 多目标耦合方式 | 等权重 / 熵权 / AHP / TOPSIS / Pareto支配 / 纳什议价 |

### 关键操作：问题适配
拿到新问题后，第一步就是把上表的「典型等位基因」替换成**该问题领域内的标准建模选项**。

---

## 🏗️ 第二步：三层嵌套进化架构

### 三层架构概览

```
┌───────────────────────────────────────────────────┐
│ L3: 元学习层（Meta-Learner）                     │
│   频率: 每5代 或 进化停滞时                      │
│   能力: 提出新等位基因 → 代码生成 → 动态注入     │
│         → 扩展搜索空间本身                        │
│   ✅ 已实现: 等位基因代码生成+动态注入            │
│   ✅ 已实现: 进化记忆与跨问题知识迁移             │
└───────────────────────┬───────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────┐
│ L2: 建模设计搜索层（LLM-guided GA）              │
│   频率: 每一代                                     │
│   能力: 在8维空间内搜索最优建模组合               │
│   ✅ 已实现: 30% LLM智能变异 / 70% 传统随机变异   │
│   ✅ 已实现: 20% LLM语义交叉 / 80% 传统随机交叉   │
└───────────────────────┬───────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────┐
│ L1: 数值优化层（传统求解器）                      │
│   频率: 每个个体每次评估                           │
│   能力: 给定建模设计 → 找最优参数值               │
│   ✅ 已实现: Great Lakes物理仿真 + 传统求解器     │
└───────────────────────────────────────────────────┘
```

---

## 🔄 第三步：完整算法伪代码

```python
def LLM4AD_mathematical_modeling(problem_description, data):
    """
    LLM4AD通用数学建模进化主算法
    
    Args:
        problem_description: 问题文本描述
        data: 问题数据
    Returns:
        pareto_front: 帕累托最优建模算法族
        analysis_report: 完整分析报告
    """
    
    # ========== 阶段1: 问题分类 + 基因空间初始化 ==========
    problem_type = LLM_classify_problem_type(problem_description)
    # 输出: physical / network / data / socioeconomic
    
    gene_space = initialize_gene_space(problem_type)
    # 把8个维度的典型等位基因填充好
    
    population = initialize_random_population(gene_space, size=64)
    memory = EvolutionaryMemory()  # 跨问题知识迁移库
    
    # ========== 阶段2: 主进化循环 ==========
    for generation in range(1, max_generations + 1):
        
        # ---------- L1层: 评估所有个体 ----------
        for individual in population:
            # individual.genotype = {dynamics, constraints, ...}
            modeling_algorithm = instantiate_model(individual.genotype, data)
            solution = modeling_algorithm.solve()  # ← 传统数值优化在这里
            individual.fitness = evaluate_solution(solution)
            individual.objectives = extract_multi_objective_values(solution)
        
        # ---------- 计算Pareto前沿 ----------
        pareto_front = compute_pareto_front(population)
        
        # ---------- L2层: 产生下一代 ----------
        offspring = []
        while len(offspring) < population_size:
            
            # 选择父代
            p1, p2 = tournament_selection(population, k=3)
            
            # 交叉: 20% LLM语义融合，80% 传统随机交叉
            if random() < 0.2:
                c1, c2 = LLM_semantic_crossover(p1, p2, problem_description)
            else:
                c1, c2 = traditional_uniform_crossover(p1, p2)
            
            # 变异: 30% LLM智能变异，70% 传统随机变异
            for child in [c1, c2]:
                if random() < 0.3:
                    child = LLM_intelligent_mutation(child, problem_description, memory)
                else:
                    child = traditional_mutation(child, gene_space)
                offspring.append(child)
        
        # ---------- L3层: 元学习检查（每10代执行一次）----------
        if generation % 10 == 0 or evolution_stagnated(population, last_3_gens):
            
            # L3分析当前Pareto前沿瓶颈
            bottleneck_analysis = LLM_analyze_pareto_frontier(pareto_front)
            
            # L3提出新等位基因
            new_alleles = LLM_propose_new_alleles(bottleneck_analysis, problem_description)
            
            # L3扩展基因空间！核心创新点
            for locus, allele_name, description in new_alleles:
                gene_space[locus].append(allele_name)
                print(f"🧬 L3扩展搜索空间: [{locus}] + {allele_name}")
                memory.record_new_allele(locus, allele_name, problem_type)
            
            # L3注入高潜力范式个体
            paradigm_shifters = LLM_propose_radical_paradigms(pareto_front, problem_type)
            offspring.extend(paradigm_shifters)
            
            # L3更新进化记忆
            memory.update_patterns(pareto_front, problem_type)
        
        # ---------- 环境选择: 精英保留 + 拥挤度排序 ----------
        combined = population + offspring
        population = select_next_generation(combined, size=population_size)
        
        # 日志
        print(f"Gen {generation}: Best fit={max(ind.fitness for ind in population):.3f}, "
              f"Pareto size={len(pareto_front)}")
    
    # ========== 阶段3: 结果后处理 ==========
    
    # 1. Pareto前沿聚类成建模范式
    paradigm_clusters = cluster_pareto_front(pareto_front)
    # 输出: 最快范式、最鲁棒范式、最公平范式、最精确范式...
    
    # 2. 生成多维度敏感性分析
    sensitivity_report = generate_sensitivity_analysis(
        fastest_individual,           # 用最快的个体跑1000次参数扫描
        most_robust_individual        # 用最鲁棒的个体跑极端情景
    )
    
    # 3. 生成政策建议和权衡分析
    policy_report = generate_policy_recommendations(
        pareto_front,                   # 用整个前沿做权衡分析
        stakeholder_names
    )
    
    # 4. 把成功模式写入进化记忆库，供未来问题迁移
    memory.commit_generation_results(pareto_front, problem_type)
    
    return {
        "pareto_front": pareto_front,
        "paradigm_clusters": paradigm_clusters,
        "sensitivity_report": sensitivity_report,
        "policy_report": policy_report,
        "evolutionary_memory": memory
    }
```

---

## 🧠 第四步：LLM算子详细定义

### 1. LLM智能变异算子

```python
def LLM_intelligent_mutation(individual, problem_description, memory):
    """
    不是随机换一个等位基因，而是：
    1. 分析这个个体当前基因型的弱点
    2. 理解问题语义
    3. 查进化记忆，看类似问题什么等位基因表现好
    4. 有针对性地改变最应该改的那个维度
    """
    prompt = f"""
    问题描述: {problem_description}
    
    当前建模设计:
    {json.dumps(individual.genotype, indent=2)}
    
    个体性能: fitness={individual.fitness}, 目标值={individual.objectives}
    
    任务：
    1. 分析这个建模设计最大的弱点是什么？
    2. 哪个维度的改变最可能提升性能？
    3. 应该改成哪个等位基因？（可以提新的等位基因）
    
    返回JSON:
    {{
        "locus_to_mutate": "dynamics",
        "new_allele": "stochastic_process",
        "reasoning": "为什么这个改动会好",
        "is_new_allele": false
    }}
    """
    
    result = call_llm(prompt)
    
    # 如果是全新等位基因，自动加入基因空间！
    if result["is_new_allele"]:
        gene_space[result["locus_to_mutate"]].append(result["new_allele"])
    
    individual.genotype[result["locus_to_mutate"]] = result["new_allele"]
    return individual
```

### 2. LLM语义交叉算子

```python
def LLM_semantic_crossover(parent1, parent2, problem_description):
    """
    不是随机切分拼接，而是：
    1. 分析parent1的优势在哪里
    2. 分析parent2的优势在哪里
    3. 做优势的语义级融合
    """
    prompt = f"""
    问题描述: {problem_description}
    
    父代A设计: {json.dumps(parent1.genotype, indent=2)}
    父代A性能: {parent1.objectives}
    
    父代B设计: {json.dumps(parent2.genotype, indent=2)}
    父代B性能: {parent2.objectives}
    
    任务：
    1. 父代A的设计优势是什么？
    2. 父代B的设计优势是什么？
    3. 产生两个子代，在语义层面融合两个父代的优点
       （不是简单随机选基因，而是有意义的组合）
    
    返回JSON:
    {{
        "parent_a_strengths": [...],
        "parent_b_strengths": [...],
        "offspring_1": {{...}},
        "offspring_2": {{...}}
    }}
    """
    
    result = call_llm(prompt)
    return Individual(result["offspring_1"]), Individual(result["offspring_2"])
```

### 3. LLM元学习算子

```python
def LLM_propose_new_alleles(pareto_front, problem_description):
    """
    L3最核心能力：跳出当前搜索空间，提出全新的建模选项
    """
    prompt = f"""
    问题描述: {problem_description}
    
    当前Pareto前沿上的建模设计:
    {[ind.genotype for ind in pareto_front[:5]]}
    
    瓶颈分析：
    这些个体的适应度都卡在X水平，似乎遇到了搜索空间的边界。
    
    任务：
    请提出2-3个全新的等位基因（目前不在现有选项中），
    它们代表了完全不同的建模思路，有潜力突破当前性能瓶颈。
    
    注意：不要做小改动，要提范式级别的创新！
    
    返回JSON:
    {{
        "new_alleles": [
            {{
                "locus": "dynamics",
                "allele_name": "graph_neural_network_based",
                "description": "用GNN建模节点间相互作用",
                "rationale": "为什么这个范式能突破当前瓶颈",
                "expected_improvement": "15-20%"
            }},
            ...
        ]
    }}
    """
    
    result = call_llm(prompt)
    return result["new_alleles"]
```

---

## 📊 第五步：结果输出与报告生成

### 进化后你得到的**不是一个答案**，而是一整套分析工具：

| 输出物 | 用途 | 用哪个个体 | 状态 |
|--------|------|-----------|------|
| **基准模型** | 主论文用的核心模型 | Pareto最中央个体 | ✅ 已实现 |
| **敏感性分析** | 参数敏感度龙卷风图 | 运行最快的个体 | ✅ 已实现 |
| **鲁棒性报告** | 极端情景压力测试 | 最鲁棒的个体 | ✅ 已实现 |
| **范式聚类** | 不同建模范式识别 | 整个Pareto前沿 | ✅ 已实现 |
| **权衡分析** | 利益相关方帕累托曲线 | 整个Pareto前沿 | ⚠️ 待完成 |
| **政策建议** | 不同政策下的效果预测 | 多模型一致投票 | ⚠️ 待完成 |
| **方法比较** | 不同建模哲学的优劣 | 所有范式聚类中心 | ⚠️ 待完成 |

---

## 🚀 第六步：跨问题进化记忆

每次解决完一个问题，把成功的建模模式写入`EvolutionaryMemory.json`：

```json
{
    "pattern_library": {
        "physical_dynamics_problems": {
            "preferred_dynamics": ["stochastic_process", "seasonal_ode"],
            "avoid": ["static_equation"],
            "average_fitness_gain": "+22%"
        },
        "network_flow_problems": {
            "preferred_solver": ["admm_distributed", "mpc_rolling"],
            "temporal_arch": ["event_triggered", "multi_scale"]
        }
    },
    
    "discovered_allele_bank": {
        "admm_distributed": {
            "discovered_on_problem": "2024D_Great_Lakes",
            "transfer_success_count": 3,
            "problem_types": ["network", "physical"]
        }
    },
    
    "problem_archetype_rules": [
        "带季节周期性的物理问题 → 优先试stochastic_inflow",
        "多利益相关方问题 → 目标函数用chebyshev比linear好",
        "网络流问题 → solver试admm_distributed"
    ]
}
```

下次遇到新问题时，先加载这个记忆库做warm start！

---

## 💡 关键设计哲学总结

| 原则 | 含义 |
|------|------|
| **搜索建模，不搜索答案** | 先找用什么方法，再用方法找答案 |
| **算法族，不是单算法** | 每个问题用10种不同哲学的方法回答 |
| **语义进化，不是随机变异** | LLM理解建模设计再做改动 |
| **可扩展搜索空间** | 算法自己可以提出新的建模维度 |
| **跨问题知识积累** | 越用越聪明 |

---

## 📝 使用步骤（拿到新问题时）

1. **问题分类**：让LLM判断属于4类中的哪一类（物理/网络/数据/社会经济）
2. **初始化基因空间**：把8个维度填上该问题类型的标准等位基因
3. **加载进化记忆**：warm start种群，把历史上该类型的好等位基因的初始概率调高
4. **跑主进化循环**：64个体，50代
5. **后处理**：Pareto前沿聚类 → 敏感性分析 → 政策建议 → 生成报告
6. **写入记忆**：成功的模式存入进化记忆库

---

## 🔮 未来工作：从「进化方法」到「进化问题定义」

### 当前框架的根本局限

当前 LLM4AD 的 8 维进化框架有一个隐含的强假设：**我们是在"问题定义已经确定"的前提下，进化解法本身**。

这意味着我们把数学建模竞赛中最核心、最有价值的一步给跳过了。

### 美赛的本质：问题定义才是真正的战场

美赛题目只给"问题"和"背景约束"，**不给"可量化的目标函数"和"完整的约束条件"——这些需要参赛者自己定义、假设并论证其合理性。**

| 美赛参赛者需要自己做的决策 | 在当前 LLM4AD 框架中是怎么处理的 |
|---------------------------|-------------------------------|
| 纳入哪些利益相关者 | ✅ 固定为统一的 6 个目标 |
| 各目标的优先级权重 | ✅ 由 `coupling` 维度控制 |
| 选择建模哪些物理因素 | ❌ **被固定为简化框架**（冰塞、风、延迟全部去掉） |
| 目标函数形式（线性/帕累托/字典序） | ✅ 由 `objective_form` 维度控制 |
| 约束阈值设定（防洪红线多少、大坝最大出流） | ❌ **被固定为统一数值** |
| 什么叫"模型有效"的评估标准 | ❌ **被固定为 6 指标加权和** |

**更深层的洞察**：O 奖论文与其他奖项的最大区别，**往往不在解法好不好，而在问题定义牛不牛**。

| 层面 | 当前 LLM4AD 进化的 | O 奖真正比拼的 |
|------|------------------|-------------|
| 第一层 | 用什么求解器（GA / MPC / LP） | ✅ 你认为这到底是个什么问题？ |
| 第二层 | 用什么目标耦合方式（加权 / 字典序） | ✅ 哪些目标重要，哪些可以忽略？ |
| 第三层 | 用什么鲁棒性策略 | ✅ 哪些物理因素值得建模？ |
| 第四层 | —— | ✅ 这个问题的本质是优化？控制？还是博弈？ |

4 篇 O 奖论文对同一个问题的定义完全不同：
- **2417004**：问题 = 多目标帕累托优化，给决策者呈现所有非支配解
- **2417831**：问题 = 反馈控制系统设计，重点是不同模式下的控制律
- **2419588**：问题 = 利益相关者均衡博弈，重点是 ESS 满意度加权
- **2429211**：问题 = 时间延迟系统的线性规划，重点是延迟矩阵建模

在当前的简化框架下，这些最核心的建模创新都被"抹平"了，只剩下求解器和耦合方式的表面差异。

---

### 可能的进化方向

#### 方向 1：增加第 9 维「问题建模范式」

```python
gene: problem_paradigm
alleles: [
    "multi_objective_optimization",   # 多目标优化（2417004 风格）
    "feedback_control_system",         # 反馈控制系统（2417831 风格）
    "stakeholder_bargaining_game",     # 利益相关者博弈（2419588 风格）
    "time_delay_network_flow"          # 时延网络流（2429211 风格）
]
```

让 LLM 不仅选择"用什么方法解"，还进化"把这个问题看成什么类型的问题"。

#### 方向 2：增加「物理建模选择」维度

```python
gene: physical_modeling_scope
alleles: [
    "minimal_balance_only",          # 只做水量平衡（最简模型）
    "plus_seasonal_evap",            # + 季节性蒸发建模
    "plus_flow_delay",               # + 水流延迟建模
    "full_weather_coupled"           # + 风 + 冰塞 + 降水预报全建模
]
```

让 LLM 自己决定"为了这个问题的目标，应该建模到什么精细程度"，而不是用固定的简化框架。

---

### 终极愿景

当前的 LLM4AD：
> **给我一个定义好的优化问题，我自动搜索最好的解法。**

未来的 LLM4AD：
> **给我一段模糊的自然语言问题描述，我自动探索 10 种不同的问题定义方式，对每种定义找出最好的解法，然后告诉你哪种问题定义+解法的组合可能是最有洞察的。**

这才是真正的——**让 LLM 从零开始，自动完成数学建模竞赛的全过程。** 🚀

---

*这就是LLM4AD通用数学建模进化算法的完整设计。从拿到问题到输出全套分析，全程不需要人类做「选什么模型」这个关键决策——让进化来选！* 🚀
