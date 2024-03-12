# AWS-with-Terraform

1. An architecture diagram with short explanations of the technologies chosen

Architecture diagram:

                Kinesis Stream -> Lambda Function (Event Processor) -> Dynamodb -> S3 Bucket
                                                                        
                                        +------------------+           
                                        |                  |           
                                        |   AWS Kinesis    |           
                                        |                  |           
                                        +---------+--------+           
                                                |                      
                                   +----------------------------+      
                                   |    Lambda Function         |      
                                   |    (Event Processing &     |      
                                   |    Transformation)         |      
                                   +-------------+--------------+      
                                                |   
                                        +-----------------+             
                                        |                 |             
                                        |    Dynamodb     |             
                                        |                 |             
                                        +-----------------+   
                                                |                  
                                        +-----------------+             
                                        |                 |             
                                        |    S3 Bucket    |             
                                        |                 |             
                                        +-----------------+             

2. Technologies Chosen:

        - AWS Kinesis Data Streams: For real-time event ingestion and processing. It provides scalability, durability, and can quickly process and deliver data in real-time with minimal delay.

        - AWS Lambda: For serverless event processing. It can handle varying amounts of incoming events and easily trigger Lambda functions based on events from other AWS services, allowing smooth interactions.

        - AWS S3: For storing transformed data. It offers scalable, durable, cost-effective and secure object storage, making it ideal for storing large volumes of data reliably.

        - AWS DynamoDB: For maintaining a record of processed event UUIDs to handle deduplication efficiently.

        - Terraform: For infrastructure as code, allows you to set up and manage AWS resources by describing it in a straightforward way, saving time and reducing the chance of errors.



3. Answers to the design questions:

    3.1 How would you handle the duplicate events? What quality metrics would you define for the input data?

       - To handle duplicate events, I used DynamoDB with the event_uuid as the primary key to ensure unique entries. Before writing an event to S3, I check if the event_uuid exists in DynamoDB. If it exists, I skip processing to avoid duplicates.

       - Quality metrics:

          - Uniqueness: Percentage of unique event_uuid values.
          - Completeness: Percentage of events with all required fields. (e.g., "event_name", "created_at", "event_uuid")
          - Validity: Percentage of events with valid field formats (e.g., correct formats for timestamp and event_uuid).


   3.2 How would you partition the data to ensure good performance and scalability? Would your proposed solution still be the same if the amount of events is 1000 times smaller or bigger?

       - For good performance and scalability, partitioning the data in S3 by event_type, date and unique id (e.g., year=2021/month=07/day=15/event_type=account/event_subtype=created/unique id = event_uuid) is effective. This structure supports efficient querying by event type and date range. If the event volume is 1000 times smaller or larger, this approach still works due to its scalability. One can consider increasing the number of shards in kinesis stream.
                

   3.3 What format would you use to store the data?

        - For storing the data in S3, JSON is used. JSON is human-readable and easy to work with. It also allows for flexibility and easy parsing. Which makes it efficient for both storage and retrieval.
