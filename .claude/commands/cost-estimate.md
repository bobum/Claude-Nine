# Cost Estimate

Estimate API costs before running the orchestrator.

## Claude Sonnet 4.5 Pricing

| Token Type | Cost per Million |
|------------|------------------|
| Input | $3.00 |
| Output | $15.00 |

## Quick Estimate

### By Number of Tasks

Rough estimates per task (varies by complexity):

| Task Complexity | Input Tokens | Output Tokens | Est. Cost |
|-----------------|--------------|---------------|-----------|
| Simple | ~10,000 | ~5,000 | ~$0.11 |
| Medium | ~25,000 | ~15,000 | ~$0.30 |
| Complex | ~50,000 | ~30,000 | ~$0.60 |
| Very Complex | ~100,000 | ~50,000 | ~$1.05 |

**Example**: 4 medium tasks ≈ $1.20

### By Description Length

Longer descriptions = more input tokens:

```bash
# Count words in task file
wc -w claude-multi-agent-orchestrator/tasks/my_tasks.yaml

# Rough token estimate (1 word ≈ 1.3 tokens)
words=$(wc -w < claude-multi-agent-orchestrator/tasks/my_tasks.yaml)
echo "Estimated input tokens per task: $((words * 13 / 10))"
```

## Estimate Calculator

### Manual Calculation

```bash
# Variables (adjust these)
NUM_TASKS=4
AVG_INPUT_TOKENS=25000
AVG_OUTPUT_TOKENS=15000

# Calculate
TOTAL_INPUT=$((NUM_TASKS * AVG_INPUT_TOKENS))
TOTAL_OUTPUT=$((NUM_TASKS * AVG_OUTPUT_TOKENS))
INPUT_COST=$(echo "scale=2; $TOTAL_INPUT * 3 / 1000000" | bc)
OUTPUT_COST=$(echo "scale=2; $TOTAL_OUTPUT * 15 / 1000000" | bc)
TOTAL_COST=$(echo "scale=2; $INPUT_COST + $OUTPUT_COST" | bc)

echo "Tasks: $NUM_TASKS"
echo "Input tokens: $TOTAL_INPUT (\$$INPUT_COST)"
echo "Output tokens: $TOTAL_OUTPUT (\$$OUTPUT_COST)"
echo "Estimated total: \$$TOTAL_COST"
```

### Python Script

```python
# cost_estimate.py
import yaml
import sys

# Pricing (per million tokens)
INPUT_PRICE = 3.00
OUTPUT_PRICE = 15.00

# Complexity multipliers (adjust based on experience)
COMPLEXITY = {
    'simple': {'input': 10000, 'output': 5000},
    'medium': {'input': 25000, 'output': 15000},
    'complex': {'input': 50000, 'output': 30000},
    'very_complex': {'input': 100000, 'output': 50000}
}

def estimate_task_complexity(description: str) -> str:
    """Estimate complexity from description length."""
    word_count = len(description.split())
    if word_count < 50:
        return 'simple'
    elif word_count < 150:
        return 'medium'
    elif word_count < 300:
        return 'complex'
    else:
        return 'very_complex'

def estimate_costs(tasks_file: str):
    with open(tasks_file) as f:
        tasks = yaml.safe_load(f)

    total_input = 0
    total_output = 0

    print(f"{'Task':<30} {'Complexity':<12} {'Input':<10} {'Output':<10} {'Cost':<8}")
    print("-" * 70)

    for feature in tasks.get('features', []):
        name = feature.get('name', 'unnamed')[:30]
        desc = feature.get('description', '')
        complexity = estimate_task_complexity(desc)
        tokens = COMPLEXITY[complexity]

        input_tokens = tokens['input']
        output_tokens = tokens['output']
        cost = (input_tokens * INPUT_PRICE + output_tokens * OUTPUT_PRICE) / 1_000_000

        total_input += input_tokens
        total_output += output_tokens

        print(f"{name:<30} {complexity:<12} {input_tokens:<10} {output_tokens:<10} ${cost:.2f}")

    total_cost = (total_input * INPUT_PRICE + total_output * OUTPUT_PRICE) / 1_000_000
    print("-" * 70)
    print(f"{'TOTAL':<30} {'':<12} {total_input:<10} {total_output:<10} ${total_cost:.2f}")

    return total_cost

if __name__ == '__main__':
    tasks_file = sys.argv[1] if len(sys.argv) > 1 else 'tasks/example_tasks.yaml'
    estimate_costs(tasks_file)
```

Run:
```bash
cd claude-multi-agent-orchestrator
python cost_estimate.py tasks/my_tasks.yaml
```

## Historical Cost Analysis

### From Previous Runs

```bash
# Get actual costs from completed runs
sqlite3 api/claude_nine.db "
SELECT
  r.session_id,
  SUM(json_extract(rt.telemetry_data, '$.token_usage.cost_usd')) as cost
FROM runs r
JOIN run_tasks rt ON r.id = rt.run_id
WHERE r.status = 'completed'
GROUP BY r.id
ORDER BY r.created_at DESC
LIMIT 10;
"
```

### Average Cost Per Task

```bash
sqlite3 api/claude_nine.db "
SELECT
  AVG(json_extract(telemetry_data, '$.token_usage.cost_usd')) as avg_cost_per_task
FROM run_tasks
WHERE status = 'completed'
  AND telemetry_data IS NOT NULL;
"
```

## Cost Optimization Tips

### 1. Use Dry-Run for Testing

```bash
# Test workflow without API costs
python orchestrator.py --dry-run --tasks tasks.yaml
```

### 2. Write Concise Descriptions

- Shorter descriptions = fewer input tokens
- Be specific but not verbose
- Use bullet points instead of paragraphs

### 3. Batch Similar Tasks

- Multiple small tasks in one run share overhead
- Better than running many single-task runs

### 4. Review Before Running

```bash
# Always preview task count and descriptions
cat tasks/my_tasks.yaml | grep -E "^  - name:|description:"
```

### 5. Set Budget Alerts

Monitor spending in Anthropic console:
https://console.anthropic.com/settings/billing

## Cost Comparison

| Approach | 10 Tasks | 50 Tasks | 100 Tasks |
|----------|----------|----------|-----------|
| Simple tasks | ~$1.10 | ~$5.50 | ~$11.00 |
| Medium tasks | ~$3.00 | ~$15.00 | ~$30.00 |
| Complex tasks | ~$6.00 | ~$30.00 | ~$60.00 |

## Before You Run

Checklist:
- [ ] Review task count
- [ ] Estimate complexity per task
- [ ] Calculate total estimate
- [ ] Verify within budget
- [ ] Consider dry-run first for complex workflows
- [ ] Have monitoring ready for long runs
