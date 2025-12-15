# Lambda + SQS Integration - Learning Notes

## Two Lambda Usage Patterns

### 1. API Gateway + Lambda (Synchronous)
```
User → API Gateway → Lambda → Response
```
- **Use case**: REST APIs, webhooks
- **Invocation**: Synchronous (user waits for response)
- **Trigger**: HTTP request
- **Example**: Yesterday's work - HTTP endpoint that returns data

### 2. SQS + Lambda (Asynchronous Worker)
```
Producer → SQS Queue → Lambda (auto-polls) → Processes messages
```
- **Use case**: Background jobs, async processing, workers
- **Invocation**: Asynchronous (no user waiting)
- **Trigger**: SQS messages
- **Example**: Job crawling/parsing workers

---

## How SQS + Lambda Integration Works

### Key Concept: Lambda PULLS from SQS (Not Push)

**SQS is pull-based:**
- Consumers must poll SQS to retrieve messages
- SQS does NOT push messages to consumers

**Lambda's Event Source Mapping:**
- Lambda service automatically polls SQS for you
- You don't write polling code
- Lambda invokes your function when messages are available
- Lambda handles message deletion after successful processing

### Flow Diagram
```
1. Producer sends messages to SQS
   ↓
2. Lambda service continuously polls SQS (behind the scenes)
   ↓
3. When messages available → Lambda invokes your function
   ↓
4. Your function processes batch of messages
   ↓
5. If successful → Lambda deletes messages from SQS
   If failed → Messages return to queue (retry logic)
```

---

## Event Source Mapping Configuration

When you configure Lambda to read from SQS, you set up an "Event Source Mapping":

```python
# AWS Console or Terraform/CloudFormation
{
  'EventSourceArn': 'arn:aws:sqs:us-east-1:123456789:my-queue',
  'FunctionName': 'my-lambda-function',
  'BatchSize': 10,                        # Process 1-10 messages per invocation
  'MaximumBatchingWindowInSeconds': 5,    # Wait up to 5s to collect batch
  'Enabled': True
}
```

**What Lambda does automatically:**
1. Polls your SQS queue continuously
2. Batches messages (up to BatchSize)
3. Invokes your function with the batch
4. Deletes messages if function succeeds
5. Returns failed messages to queue for retry

---

## Lambda Function Example

```python
import json
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda automatically invokes this when SQS messages are available

    event['Records'] contains batch of SQS messages (1-10 messages)
    """

    for record in event['Records']:
        # Parse SQS message
        message = json.loads(record['body'])
        url = message['url']
        company = message['company']

        # Process the job
        print(f"Processing {url}")

        # Your crawling logic here
        # ...

    # If function succeeds, Lambda auto-deletes messages from SQS
    # If function fails, messages go back to queue for retry
    return {'statusCode': 200}
```

**Event structure:**
```json
{
  "Records": [
    {
      "messageId": "059f36b4-87a3-44ab-83d2-661975830a7d",
      "receiptHandle": "AQEBwJnKyrHigUMZj6rYigCgxlaS3SLy0a...",
      "body": "{\"url\": \"https://jobs.google.com/123\", \"company\": \"google\"}",
      "attributes": {
        "ApproximateReceiveCount": "1",
        "SentTimestamp": "1545082649183"
      }
    }
  ]
}
```

---

## Pricing Breakdown

### Lambda Pricing

**Two components:**
1. **Invocation count** (requests)
2. **Compute time** (duration × memory)

**Pricing (us-east-1):**
- **Requests**: $0.20 per 1M requests
- **Compute**: $0.0000166667 per GB-second

**Free tier (monthly):**
- 1M requests
- 400,000 GB-seconds

**Important: Lambda polling SQS is FREE**
- Lambda service polling SQS does NOT count as invocations
- You only pay when Lambda **executes your function**
- Polling happens automatically in the background at no cost

**Example: Job Crawler (520 jobs/day)**

```
Monthly invocations:
  520 jobs/day × 30 days = 15,600 jobs/month
  BatchSize = 10 → 15,600 / 10 = 1,560 Lambda invocations/month

Request cost:
  1,560 invocations < 1M free tier → $0

Compute cost (assuming 512MB RAM, 5s per invocation):
  1,560 invocations × 5s × 0.5GB = 3,900 GB-seconds
  3,900 < 400,000 free tier → $0

Total Lambda cost: $0 (within free tier)
```

---

### SQS Pricing

**Two components:**
1. **Requests** (send, receive, delete)
2. **Data transfer** (usually free within AWS)

**Pricing:**
- **First 1M requests/month**: FREE
- **After 1M**: $0.40 per 1M requests (Standard Queue)

**What counts as a request:**
- `SendMessage` (publishing to queue)
- `ReceiveMessage` (polling queue)
- `DeleteMessage` (removing from queue)
- Empty `ReceiveMessage` also counts!

**Important: Lambda polling counts as SQS requests**
- Lambda continuously polls SQS (even when empty)
- Each poll = 1 SQS request
- BUT: Lambda uses long polling (efficient)

**Example: Job Crawler (520 jobs/day)**

```
Requests breakdown:

1. SendMessage (publishing jobs):
   520 jobs/day × 30 days = 15,600 messages/month

2. ReceiveMessage (Lambda polling):
   Lambda long-polls every ~20 seconds when queue has traffic
   With batching, roughly 2,000 polls/month

3. DeleteMessage (after processing):
   15,600 deletes/month

Total SQS requests:
  15,600 + 2,000 + 15,600 = 33,200 requests/month

Cost:
  33,200 < 1M free tier → $0

Total SQS cost: $0 (within free tier)
```

---

## Polling Behavior Deep Dive

### Lambda's Automatic Polling

**How Lambda polls SQS:**
1. Lambda service runs polling workers (not your code)
2. Workers use **long polling** (wait up to 20s for messages)
3. When messages arrive → Lambda invokes your function
4. Lambda scales polling workers based on queue depth

**Polling frequency:**
- **Active queue** (has messages): Continuous polling
- **Empty queue**: Polling slows down (but still happens)
- **Queue depth increases**: Lambda increases polling workers

**Cost implications:**
- Polling itself: FREE for Lambda
- SQS receives empty polls: Counts as SQS requests (but minimal with long polling)
- Only your function execution costs money

### Long Polling vs Short Polling

**Short polling (default for manual polling):**
- Returns immediately (even if queue empty)
- Many empty responses → wasteful requests
- Higher SQS costs

**Long polling (Lambda uses this):**
- Waits up to 20 seconds for messages
- Reduces empty responses by ~99%
- Much more cost-efficient
- Lambda automatically uses long polling

---

## Cost Comparison: Lambda vs EC2

### Scenario: 520 jobs/day, each takes 5 seconds

**Lambda:**
```
Invocations: 1,560/month (with batch size 10)
Compute: 3,900 GB-seconds/month
Cost: $0 (free tier)

Even without free tier:
Request: 1,560 × $0.0000002 = $0.0003
Compute: 3,900 × $0.0000166667 = $0.065
Total: ~$0.07/month
```

**EC2 (t3.small, 2 vCPU, 2GB RAM):**
```
Running 24/7: $15/month (on-demand)
Reserved 1-year: ~$10/month
Spot instances: ~$5/month (but can be interrupted)

Note: EC2 runs continuously even when no jobs
```

**Lambda is 150-200x cheaper for this workload!**

---

## Retry and Error Handling

### Automatic Retries

**Lambda + SQS retry flow:**
1. Lambda receives message batch
2. Your function throws error
3. Lambda does NOT delete messages from SQS
4. Messages return to queue after visibility timeout
5. Lambda will retry later

**Visibility timeout:**
- When Lambda receives message, it becomes invisible to other consumers
- Default: 30 seconds
- If processing fails, message becomes visible again after timeout
- Configure based on your function timeout

**MaxReceiveCount (Dead Letter Queue):**
```python
# SQS Queue configuration
{
  'RedrivePolicy': {
    'deadLetterTargetArn': 'arn:aws:sqs:us-east-1:123456789:my-dlq',
    'maxReceiveCount': 3  # Retry 3 times, then move to DLQ
  }
}
```

### Best Practices

1. **Set visibility timeout > Lambda timeout**
   ```
   Lambda timeout: 30s
   SQS visibility timeout: 35s (add buffer)
   ```

2. **Configure Dead Letter Queue (DLQ)**
   ```
   Failed after 3 retries → Move to DLQ for investigation
   ```

3. **Use batch processing carefully**
   ```python
   # If one message in batch fails, entire batch fails!
   # Solution: Process each message individually, catch errors

   def lambda_handler(event, context):
       failed_messages = []

       for record in event['Records']:
           try:
               process_message(record)
           except Exception as e:
               failed_messages.append(record)
               print(f"Failed: {record['messageId']}, error: {e}")

       # Optionally: Raise error to retry failed messages
       if failed_messages:
           raise Exception(f"Failed to process {len(failed_messages)} messages")
   ```

---

## Key Takeaways

1. **Lambda polling SQS is FREE** (doesn't count as Lambda invocations)
2. **Lambda pulls from SQS** (not push-based)
3. **Lambda uses long polling** (very efficient for SQS costs)
4. **You only pay when Lambda executes your function**
5. **SQS requests from Lambda polling are minimal** (long polling reduces empty polls)
6. **For 520 jobs/day, both Lambda and SQS are within free tier** ($0 cost)
7. **Lambda is 150-200x cheaper than EC2** for sporadic workloads
8. **Lambda auto-scales** (no need to manage workers)

---

## When to Use Lambda vs EC2/ECS

### Use Lambda when:
- ✅ Sporadic workload (not 24/7)
- ✅ Tasks complete in < 15 minutes
- ✅ Memory < 10GB
- ✅ Simple HTTP/SQS triggers
- ✅ Want zero infrastructure management

### Use EC2/ECS when:
- ❌ Tasks take > 15 minutes
- ❌ Need > 10GB RAM or GPUs
- ❌ Persistent connections (WebSockets)
- ❌ Continuous high-volume processing (24/7)
- ❌ Complex custom dependencies

**For job crawling (520 jobs/day, 5s each): Lambda is perfect!**

---

## Next Steps

1. Set up SQS queues (crawl-queue, parse-queue)
2. Create Lambda functions (crawler, parser)
3. Configure Event Source Mapping
4. Set up DLQ for failed messages
5. Monitor with CloudWatch

---

## References

- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [AWS SQS Pricing](https://aws.amazon.com/sqs/pricing/)
- [Lambda Event Source Mapping](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [SQS Long Polling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html)
