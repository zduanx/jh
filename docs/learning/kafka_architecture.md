# Kafka Architecture - Learning Notes

## What is Kafka?

Apache Kafka is a **distributed event streaming platform** designed for high-throughput, fault-tolerant message processing.

**Key characteristics:**
- Persistent append-only log (like a database WAL)
- Distributed and replicated across multiple brokers
- Supports message replay (consumers can re-read old messages)
- Extremely high throughput: 1-3M messages/sec per cluster

---

## Kafka vs SNS+SQS

### Comparison Table

| Feature | Kafka | SNS + SQS |
|---------|-------|-----------|
| **Architecture** | Distributed log | Pub/Sub + Queue |
| **Persistence** | Persistent (days/weeks) | Temporary (up to 14 days) |
| **Replay** | ✅ Yes (seek to any offset) | ❌ No (once deleted, gone) |
| **Message ordering** | ✅ Per partition | ⚠️ FIFO queue only |
| **Throughput** | Very high (1-3M msg/sec) | Medium (3K msg/sec standard) |
| **Latency** | Low (2-10ms) | Medium (10-100ms) |
| **Use case** | Event streaming, analytics | Message delivery, fanout |
| **Complexity** | High (self-managed) | Low (fully managed) |
| **Cost** | Infrastructure cost | Per-request cost |

### When to Use What?

**Use Kafka when:**
- ✅ Need message replay / event sourcing
- ✅ Building event-driven architecture
- ✅ Real-time analytics / stream processing
- ✅ Very high throughput (millions of messages/sec)
- ✅ Multiple consumers need to read same data
- ✅ Need exactly-once semantics

**Use SNS + SQS when:**
- ✅ Simple message delivery
- ✅ Don't need replay
- ✅ Want fully managed service (no ops)
- ✅ Sporadic workloads (not 24/7)
- ✅ Cost-sensitive for low volume

**For job crawling (520 jobs/week): SNS+SQS is better** (simpler, cheaper, fully managed)

---

## Kafka Core Concepts

### 1. Topics and Partitions

```
Topic: "user-events" (logical stream)
├── Partition 0: [msg0, msg1, msg2, msg3, ...]
├── Partition 1: [msg4, msg5, msg6, msg7, ...]
└── Partition 2: [msg8, msg9, msg10, msg11, ...]

Each partition is an ordered, immutable log
```

**Key points:**
- Topic = logical stream (like a database table)
- Partition = physical file on disk (ordered log)
- Messages within a partition are ordered
- Messages across partitions are NOT ordered
- Partitions enable horizontal scaling

---

### 2. Producers and Consumers

```
Producer → Kafka Topic (3 partitions) → Consumer Group A
                                      → Consumer Group B

Producer:
  - Sends messages to topics
  - Decides which partition (by key or round-robin)
  - Can batch messages for efficiency

Consumer:
  - Reads messages from partitions
  - Tracks offset (position in log)
  - Can replay by resetting offset
```

**Consumer Groups:**
```
Topic with 3 partitions, Consumer Group with 3 consumers:

Partition 0 → Consumer 1
Partition 1 → Consumer 2
Partition 2 → Consumer 3

Each partition assigned to ONE consumer in the group
Multiple groups can read the SAME data independently
```

---

## Kafka Performance: How Does It Achieve 1M+ Messages/Sec?

### Sequential Writes vs Random Writes

**The Key Insight: Sequential disk writes are FAST**

```
Modern SSD Performance:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Random writes:     50-100 MB/s    (database-style)
Sequential writes: 500-3000 MB/s  (10-30x faster!)

Modern HDD Performance:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Random writes:     1-5 MB/s       (very slow)
Sequential writes: 100-200 MB/s   (50-100x faster!)
```

**Why is sequential so much faster?**
- No disk seek time (head doesn't move)
- OS can optimize with large writes
- Hardware controller can optimize
- Can leverage write caching effectively

---

### How Kafka Uses Sequential Writes

**Kafka IS a Write-Ahead Log (WAL)**

```
Traditional Database:
  Write → Update B-tree index → Update data file → Sync
  (Random writes to multiple locations)

Kafka:
  Write → Append to partition log → Sync
  (Sequential write to one file)
```

**Example: Writing 1 million messages**

```
Database (random writes):
  1M writes × 100 µs per random write = 100 seconds

Kafka (sequential writes):
  1M messages × 1KB = 1GB
  1GB ÷ 1000 MB/s = 1 second

Kafka is 100x faster!
```

---

### Kafka's Performance Optimizations

#### 1. Batching

```python
# Without batching (slow)
for i in range(1000):
    producer.send('topic', f'message-{i}')
    # Each message: 1 network round-trip + 1 disk write
    # Total: 1000 network calls + 1000 disk writes

# With batching (fast)
producer = KafkaProducer(
    batch_size=16384,      # 16KB batches
    linger_ms=10,          # Wait 10ms to fill batch
)

for i in range(1000):
    producer.send('topic', f'message-{i}')
    # Batched: ~10 network calls + ~10 disk writes
    # 100x faster!
```

**Why batching helps:**
- Amortizes network overhead (1 TCP packet for 100 messages)
- Amortizes disk overhead (1 fsync for 100 messages)
- Better compression (compress 100 messages together)

---

#### 2. Page Cache

```
Kafka relies heavily on OS page cache:

Write path:
  Producer → Kafka → Write to page cache (RAM) → Return
                   → OS flushes to disk asynchronously

Read path:
  Consumer → Kafka → Read from page cache (RAM) → Return
                   → No disk read needed (if recent)

Result:
  - Writes are fast (RAM speed)
  - Reads are fast (RAM speed for recent data)
  - OS handles disk I/O efficiently
```

**Page cache benefits:**
- RAM is 1000x faster than disk
- Recent messages stay in RAM
- OS manages memory better than JVM
- Zero-copy transfer (see below)

---

#### 3. Zero-Copy

**Traditional file serving:**
```
Disk → OS buffer → Application buffer → Socket buffer → Network
       (copy 1)       (copy 2)            (copy 3)

3 data copies + 4 context switches
```

**Kafka's zero-copy (sendfile()):**
```
Disk → OS buffer → Network
       (DMA transfer, no CPU involvement)

0 data copies + 2 context switches
Result: 2-3x faster, lower CPU usage
```

---

#### 4. Partitioning

**Horizontal scaling through partitions:**

```
Single partition:
  1 disk × 500 MB/s = 500 MB/s

10 partitions on 10 disks:
  10 disks × 500 MB/s = 5000 MB/s

Result: 10x throughput through parallelism
```

**Partition distribution:**
```
Topic: "user-events" with 10 partitions, 3 brokers

Broker 1: Partitions 0, 3, 6, 9
Broker 2: Partitions 1, 4, 7
Broker 3: Partitions 2, 5, 8

Writes distributed across all brokers (parallel I/O)
```

---

#### 5. Compression

```python
producer = KafkaProducer(
    compression_type='lz4',  # or snappy, gzip, zstd
)

# Before compression: 1KB message
# After compression: ~300 bytes (70% reduction)

Result:
  - 3x less network bandwidth
  - 3x less disk space
  - 3x more messages per batch
  - 30-50% higher throughput
```

---

## Kafka Fault Tolerance

### Replication Architecture

```
Topic: "orders" with 3 partitions, replication factor = 3

Partition 0:
  Leader: Broker 1 (handles reads/writes)
  Follower: Broker 2 (replicates from leader)
  Follower: Broker 3 (replicates from leader)

Partition 1:
  Leader: Broker 2
  Follower: Broker 1
  Follower: Broker 3

Partition 2:
  Leader: Broker 3
  Follower: Broker 1
  Follower: Broker 2

Each broker is leader for some partitions, follower for others
```

---

### Write Path with Replication

```
Producer sends message with acks='all':

1. Message arrives at Leader (Broker 1)
2. Leader writes to local WAL (disk) ✅
3. Leader sends to Follower 1 (Broker 2)
4. Leader sends to Follower 2 (Broker 3)
5. Follower 1 writes to WAL → Sends ACK ✅
6. Follower 2 writes to WAL → Sends ACK ✅
7. Leader receives ACKs from all followers
8. Leader sends ACK to producer ✅
9. Producer considers message delivered

Total latency: 5-15ms
```

**Key insight: Pipelined replication**
- Leader doesn't wait for ACK before sending next batch
- Followers write to disk in parallel
- Leader tracks which followers are caught up (ISR)

---

### In-Sync Replicas (ISR)

```
Partition 0 replicas:
  Leader: Broker 1 (offset: 1000)
  Follower 1: Broker 2 (offset: 1000) ✅ In ISR
  Follower 2: Broker 3 (offset: 995)  ❌ Not in ISR (lagging)

ISR = [Broker 1, Broker 2]

Only in-sync replicas can become leader
Lagging replicas must catch up to rejoin ISR
```

**Why ISR matters:**
- Prevents data loss on leader failure
- Only caught-up replicas can become new leader
- Guarantees durability with `acks='all'`

---

### Acknowledgment Modes (acks)

```python
# acks=0: Fire and forget (no durability)
producer = KafkaProducer(acks=0)
# Producer doesn't wait for any ACK
# Throughput: Highest (1-3M msg/sec)
# Risk: Message loss if broker crashes

# acks=1: Leader acknowledgment only
producer = KafkaProducer(acks=1)
# Producer waits for leader to write to disk
# Throughput: Medium (800K-1M msg/sec)
# Risk: Message loss if leader crashes before replication

# acks='all': All in-sync replicas
producer = KafkaProducer(acks='all')
# Producer waits for all ISR to acknowledge
# Throughput: Lower (200K-500K msg/sec)
# Risk: Minimal (data replicated to all ISR)
```

---

### Fault Tolerance Guarantees

**Scenario 1: Leader crashes after writing to local WAL**

```
Timeline:
1. Producer sends message
2. Leader (Broker 1) writes to WAL ✅
3. Leader starts sending to followers
4. 💥 Leader crashes (before followers receive)

Result with acks='all':
  - Producer does NOT receive ACK
  - Producer retries
  - New leader elected from ISR
  - Producer sends to new leader
  - ✅ No message loss (from producer's perspective)

Result with acks=1:
  - Producer received ACK from old leader
  - Message was on old leader's disk
  - Old leader offline → data lost
  - ❌ Message lost (producer thinks it's delivered)
```

**Scenario 2: Follower crashes**

```
Timeline:
1. Leader and 2 followers in ISR
2. 💥 Follower 1 crashes
3. Leader continues with Follower 2
4. ISR shrinks to [Leader, Follower 2]
5. Writes continue normally
6. Follower 1 restarts, catches up, rejoins ISR

Result:
  - ✅ No data loss
  - ✅ No downtime
  - ISR dynamically adjusts
```

---

## Producer-Side Fault Tolerance

### Batching Risk Window

```
Timeline of producer batching:
t=0ms:   msg1 arrives → In producer memory
t=3ms:   msg2 arrives → In producer memory
t=5ms:   msg3 arrives → In producer memory
t=7ms:   💥 PRODUCER CRASHES
         → msg1, msg2, msg3 LOST (never sent to Kafka)

Risk window: linger_ms (default 0, typically set to 10-20ms)
```

**Messages in producer memory are NOT durable until:**
1. Sent to Kafka broker
2. Acknowledged by broker (based on `acks` setting)

---

### Producer Durability Patterns

#### Pattern 1: Blocking Confirmation

```python
producer = KafkaProducer(
    acks='all',
    linger_ms=0,  # Send immediately
)

# Block until ACK received
future = producer.send('topic', message)
metadata = future.get(timeout=10)  # BLOCKS here

# Only continues after Kafka acknowledges
# Risk window: Minimal (only network latency)
# Throughput: Low (~100K msg/sec)
```

---

#### Pattern 2: Async with Callbacks

```python
def on_success(metadata):
    print(f"✅ Sent to {metadata.topic} offset {metadata.offset}")

def on_error(e):
    print(f"❌ Failed: {e}")
    # Log to DB, retry, or alert

producer = KafkaProducer(
    acks='all',
    linger_ms=10,
)

# Async send
future = producer.send('topic', message)
future.add_callback(on_success)
future.add_errback(on_error)

# Risk: If producer crashes before callback, message lost
# Throughput: High (400K-500K msg/sec with batching)
```

---

#### Pattern 3: Persist-Before-Send (Transactional Outbox)

```python
# For critical data (orders, payments, etc.)
def send_critical_message(message):
    # 1. Save to local database FIRST (durable)
    db.insert('pending_messages', {
        'message': message,
        'status': 'pending',
        'created_at': now()
    })

    # 2. Send to Kafka
    try:
        future = producer.send('topic', message)
        metadata = future.get(timeout=10)

        # 3. Mark as sent
        db.update('pending_messages', {'status': 'sent'})
    except Exception as e:
        # Message safely stored in DB for retry
        log.error(f"Failed: {e}")

# Background worker retries unsent messages
def retry_worker():
    pending = db.query('pending_messages', status='pending')
    for msg in pending:
        # Retry...
```

**Guarantees:**
- ✅ No message loss (persisted locally)
- ✅ Survives producer crashes
- ✅ Retry mechanism

**Trade-offs:**
- ⚠️ Requires database
- ⚠️ More complex
- ⚠️ Slightly higher latency

---

## Kafka Throughput Benchmarks

### Single Partition Performance

```
Configuration: 1KB messages, 1 partition, RF=3

acks=0 (no durability):
  Throughput: 1-3M msg/sec
  Latency: <1ms

acks=1 (leader only):
  Throughput: 800K-1M msg/sec
  Latency: 2-5ms

acks='all' without batching:
  Throughput: 100-200K msg/sec
  Latency: 5-15ms

acks='all' with batching + compression:
  Throughput: 400-500K msg/sec
  Latency: 5-15ms (batching adds linger_ms delay)
```

---

### Multi-Partition Cluster Performance

```
Configuration: 3 brokers, 30 partitions, RF=3, acks='all'

Single producer, single partition:
  ~400K msg/sec

Single producer, 30 partitions (round-robin):
  ~5-10M msg/sec
  (Different leaders handle requests in parallel)

10 producers, 30 partitions:
  ~20-30M msg/sec

100 producers, 100 partitions, 10 brokers:
  ~50-100M msg/sec
```

---

### Replication Factor Impact

```
Same producer throughput, different cluster load:

RF=1 (no replication):
  Producer: 1M msg/sec
  Cluster disk writes: 1M writes/sec
  Network: Producer → Broker

RF=3 (typical production):
  Producer: 1M msg/sec
  Cluster disk writes: 3M writes/sec
  Network: Producer → Leader + Leader → 2 Followers

Producer throughput: ~same (pipelined replication)
Cluster resource usage: 3x (but worth it for durability)
```

---

### Throughput Optimization Techniques

#### 1. Increase Batch Size

```python
# Default
producer = KafkaProducer(batch_size=16384)  # 16KB
# Throughput: 400K msg/sec

# Optimized
producer = KafkaProducer(batch_size=32768)  # 32KB
# Throughput: 600K msg/sec (50% improvement)
```

---

#### 2. Enable Compression

```python
producer = KafkaProducer(
    acks='all',
    compression_type='lz4',  # Fast compression
)

# Impact:
# - 50-70% less network bandwidth
# - 30-50% higher throughput
# - Slightly higher CPU usage (marginal)
```

---

#### 3. Tune linger.ms

```python
# Low latency (default)
producer = KafkaProducer(linger_ms=0)
# Each message sent immediately
# Throughput: 200K msg/sec

# Optimized for throughput
producer = KafkaProducer(linger_ms=20)
# Wait 20ms to batch more messages
# Throughput: 500K msg/sec (2.5x improvement)
# Trade-off: +20ms latency
```

---

#### 4. Use Multiple Partitions

```
Single partition:
  Limited by 1 disk: 400K msg/sec

10 partitions:
  10 disks in parallel: 4M msg/sec

100 partitions:
  Limited by network/CPU: 20-40M msg/sec
```

---

#### 5. Tune min.insync.replicas

```python
# Conservative (wait for all 3 replicas)
min.insync.replicas=3
# Slowest replica determines latency
# Throughput: 400K msg/sec

# Balanced (wait for 2 out of 3)
min.insync.replicas=2
# Second-fastest replica determines latency
# Throughput: 500K msg/sec (20% improvement)
# Still very safe (2 copies confirmed)
```

---

## Real-World Kafka Deployments

### LinkedIn (Kafka creators)

```
Scale:
- 7+ trillion messages per day
- 1000+ brokers
- 100,000+ topics
- 10+ petabytes per day

Use cases:
- Activity tracking
- Operational metrics
- Log aggregation
- Stream processing
```

---

### Netflix

```
Scale:
- 4 trillion messages per day
- 700+ billion events per day
- 3000+ Kafka brokers
- 4 petabytes per day

Use cases:
- Real-time monitoring
- Recommendations
- Security logging
- A/B testing events
```

---

### Uber

```
Scale:
- 1 trillion messages per day
- 4000+ microservices
- 100+ Kafka clusters

Use cases:
- Real-time location tracking
- Ride matching
- Surge pricing
- Fraud detection
```

---

## Kafka vs Lambda+SQS for Job Crawler

### Job Crawler Requirements

```
Current scale:
- 520 jobs/week
- ~75 jobs/day
- Sporadic (not 24/7)

Processing:
- Fetch job URLs
- Parse job details
- Store in database
```

---

### Comparison for This Use Case

```
Lambda + SQS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cost: $0 (free tier)
Complexity: Low (fully managed)
Setup time: <1 hour
Throughput: 3K msg/sec (standard queue)
           Unlimited (FIFO with batching)
Replay: ❌ No
Maintenance: None

Verdict: ✅ Perfect for this use case

Kafka:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cost: $50-100/month (AWS MSK, smallest cluster)
      OR $200-500/month (self-hosted EC2)
Complexity: High (cluster management)
Setup time: Days/weeks
Throughput: 1-3M msg/sec (massive overkill)
Replay: ✅ Yes
Maintenance: Significant

Verdict: ❌ Overkill for this use case
```

**Recommendation: Use Lambda + SQS**
- 10,000x overcapacity even with SQS
- $0 vs $50-500/month
- No operational burden
- Sufficient for years of growth

**Only consider Kafka if:**
- Need to replay job postings history
- Building event-driven architecture for many services
- Planning to scale to millions of jobs/day
- Need stream processing (real-time analytics)

---

## Key Takeaways

1. **Kafka IS a WAL** (Write-Ahead Log, not "has a" WAL)
2. **Sequential writes are 10-100x faster** than random writes
3. **Batching is critical** for performance (amortizes overhead)
4. **Page cache is magic** (recent data stays in RAM)
5. **Zero-copy** reduces CPU and improves throughput 2-3x
6. **Partitioning enables horizontal scaling** (10 partitions = 10x throughput)
7. **acks='all' is only 50% slower** than acks=1 (pipelined replication)
8. **Producer batching has a risk window** (linger_ms)
9. **ISR guarantees no data loss** on leader failure
10. **Kafka is overkill for most use cases** (but powerful when needed)

---

## When You Actually Need Kafka

**Use Kafka when you need:**
- Event sourcing / CQRS architecture
- Real-time stream processing
- Message replay capability
- Very high throughput (>10K msg/sec sustained)
- Multiple consumers reading same data
- Exactly-once semantics
- Long retention (days/weeks/months)

**Your job crawler needs NONE of these** ✅ Use Lambda + SQS

---

## References

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [LinkedIn: Running Kafka at Scale](https://engineering.linkedin.com/kafka/running-kafka-scale)
- [Jay Kreps: The Log (essential reading)](https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying)
- [Confluent: Kafka Performance](https://www.confluent.io/blog/kafka-fastest-messaging-system/)
