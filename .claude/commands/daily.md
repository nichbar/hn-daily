---
description: 创建日报
---

请你作为一名资深编辑，帮助我创建一份关于 Hacker News 的日报。日报仍以 Hacker News 为唯一来源，但应面向好奇的广义读者，而不是只面向技术从业者。

## 时间

优先使用上游传入的目标日期。如果没有提供目标日期，按下面顺序获取“本地时区的昨天”并命名为 `$target_date`：

1. 先尝试 GNU/Linux 命令：
   `date -d "yesterday" +%Y-%m-%d`
2. 如果失败，再尝试 BSD/macOS 命令：
   `date -v-1d +%Y-%m-%d`

只有当第 1 条命令不可用或执行失败时，才使用第 2 条命令。

再将 `$target_date` 拆分为：

- `$year`：`YYYY`
- `$month`：`MM`
- `$draft_dir`：`drafts/$target_date`
- `$draft_yaml`：`drafts/$target_date/drafts.yaml`
- `$daily_file`：`daily/$year/$month/$target_date.md`
- `$daily_file_en`：`daily/$year/$month/$target_date.en.md`

## 进度管理（产物即状态）

每个阶段开始前，检查**当前目标日期对应的产物是否存在**来判断恢复点：

| 阶段    | 完成标志                                      | 恢复动作                     |
| ------- | --------------------------------------------- | ---------------------------- |
| Phase 1 | `$draft_dir/` 目录存在且包含至少一个 `.md` 文件 | 跳过 Phase 1，进入 Phase 2   |
| Phase 2 | `$draft_yaml` 文件存在                        | 跳过 Phase 1-2，进入 Phase 3 |
| Phase 3 | `$daily_file` 与 `$daily_file_en` 都存在      | 跳过 Phase 1-3，进入 Phase 4 |

## 工作流程

请按照以下步骤操作，使用 `Task` 工具协调各个子任务完成工作：

### 1. 收集内容 (Phase 1)

使用 `Task` 工具调用 `crawler` 子任务，并明确传入目标日期和输出目录：

```yaml
prompt: |
  目标日期：$target_date
  输出目录：$draft_dir

  抓取 20 篇 story 作为候选池，并将原始草稿写入该目录。
```

**产出**: `$draft_dir/` 目录下的草稿文件

### 2. 翻译整理信息 (Phase 2)

使用 `Task` 工具调用 `editor` 子任务：

```yaml
prompt: |
  目标日期：$target_date
  草稿目录：$draft_dir
  输出文件：$draft_yaml

  请只处理该目录下的草稿文件，筛选、翻译并生成结构化 YAML。
  请根据内容质量、信息完整度和主题分布决定最终入选故事数量。
  不要为了凑数保留弱稿，也不要设置固定篇数上限。
  最终结果应兼顾主题分布，不要只保留纯技术话题。
```

**产出**: `$draft_yaml`，整理后的高质量内容列表

### 3. 撰写内容 (Phase 3)

先写中文版，再写英文版。两篇都基于同一份 `$draft_yaml`，故事集合、排序和主题分组必须一致。英文版按 `english-writing` 技能用英文重写，不要逐句翻译中文稿。

使用 `Task` 工具调用 `writer` 子任务撰写中文版：

```yaml
prompt: |
  目标日期：$target_date
  输入文件：$draft_yaml
  输出文件：$daily_file
  语言：zh

  请基于该 YAML 撰写中文主题化日报，面向好奇的广义读者，不要默认读者是开发者。
  Front matter 必须包含 translationKey，值等于 $target_date。
  如目录不存在请创建，并写入指定输出文件。
```

再使用 `Task` 工具调用 `writer` 子任务撰写英文版：

```yaml
prompt: |
  目标日期：$target_date
  输入文件：$draft_yaml
  输出文件：$daily_file_en
  语言：en

  Write the English edition from the same YAML. Use the english-writing skill.
  Keep the same stories, order, and topic grouping as the Chinese edition.
  Front matter must include translationKey equal to $target_date.
  Create the directory if needed and write the specified output file.
```

**产出**：`$daily_file`（中文）和 `$daily_file_en`（英文）

### 4. 审核与修订 (Phase 4)

分别审核 `$daily_file` 和 `$daily_file_en`。中文版按 `chinese-writing` 审核，英文版按 `english-writing` 审核。

**循环逻辑**：

- 对每个语言文件，如果 Reviewer 返回 "PASS"，该语言完成。
- 如果 Reviewer 返回修改意见，使用 `Task` 调用 `writer` 在对应文件上修改，并再次复核。
- 每个语言最多重复 3 次。如果 3 次后仍未通过，请保存当前版本并提示用户人工介入。
- 两个语言都通过（或达到重试上限）后，任务才结束。

请务必一次性完成所有任务，过程中无需向我确认。最终同时呈现中文版和英文版路径。
