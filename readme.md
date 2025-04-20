#sheafshifter 
###née
###🍀passer

OVERVIEW:
wow this is stinky. stinky stinky stinky.
we package some libs.
lacking better options:

SETUP:
if you somehow want to reproduce the historical process of retrieving enet binding source:
`git clone sheafshifter`
`cd sheafshifter\lib`
`git clone https://github.com/aresch/pyenet`
`cd pyenet `
`git clone https://github.com/lsalzman/enet`
`cd ..\..`
prebuild:
`uv init`
`uv add cython`
`uv add setuptools`
c bindings build:
`uv add ./lib/pyenet`

#PROJECT STATUS:
[x] get distracted by protobuf-related strategies to minimize service interruption data loss
[x] benchmark python serialization and find it's 'no big deal', 'message passing really rocks'
[x] write simple best-case network handlers
[x] throw them away for satisficer-case network handlers
[x] write simple best-case concurrent lib network handler
[x] throw that away for GIL-outscaling process-level concurrency 
[x] scream and cry and gnash teeth and wail
[x] implement 'core multiprocessing network app loop'
    [x] log printing & (network <-> service protocol) i/o factored to parallel process
    [x] tuple headered intra-application message queue driven concurrency
    [x] protocol ('echo' server & in-channel 'SHUTDOWN' client) factored out!
    [] actually use protobuf to persist unprocessed tasks wrt protocol
        [] write some proto schema for intra-server buffers / queues
    [x] hand-written blocked-message-queue synchronization
        [] write existence proof against cycle / blocking detection to extend this automatically
        [] write existence proof *for* automatic cycle / blocking detection to extend this
        [] identify a linter, even a LLM API, to flash conspicuous warnings for deadlockable blocks
        [x] schedule explicit, graceful, service shutdown thru network
        [😔] schedule explicit, graceful, service shutdown through KeyboardInterrupt 
[] router protcool server protocol
    [] pick best of 2 backpressure balancing
[] api service worker protocol
    [] queue depth / batchsize normalized channel capacity status
    [] timing i guess for channel capacity * bandwidth status
    [] unwrap packets and accept type-mismatched API errors explicitly?
[] query worker protocol
    [] a .txt file with a global lock in front of it is a db if u think about it
    [] synthesize API-compliant queries from H/MI bus directives & reads from db
    [] backpressure statuses for H/MI bus, prob dont need db load balancing tho

#PROJECT SPECIFICATION NOTES:
and with that we have a wrapper around a wrapper around UDP.
it's gonna be one of *those* projects, isn't it?
    "is enet thread-safe?"
    "enet does not use any significant global variables."
for our purposes, what this means is that *we* are scheduling the 'hot loop' which interacts with our network, uh, drivers? don't think about this too hard, it'll melt your brain.
    * enet_host_service()  must be explicitly called to 'actually send/receive' network activity.
    * enet suggests a non-blocking ('0-timeout') enet_host_service() event at absolutely all times.
    * we probably care about ENET_EVENT_TYPE_RECEIVE events at both server and client.
    * because networking sucks, explicitly returning ACKs over and over again is the only legitimate methodology for advancing our distributed processing task history.
    *this unfortunately creates requirements for our api-sided clients: they will likely need to ACK our ENET_PACKET_FLAG_RELIABLES or our task routing application can't successfully abstract the routing of tasks!
we quickly reach a three-server model:
database worker: 
    accepts API queries; queries router with job_ID, requesting query_UUID.
    ACK by *using* query UUID to submit header w/ job_ID CONCATENATE query_UUID, body of client_query
    server ACKs with a checksum, database worker ACK ACKs, connection *closes*.
    database worker ends up with its own state (macabre!): job_ID CONCATENATE query_UUID, key to db's underlying client_query value, state with one of: (pending,UUID_ACK,INTE_ACK,closed)
    we need for the db worker to... retain state so that it can match return_payloads to the underlying data this was about!   
database worker eventually also:
    accepts API return_payloads; these can happen basically whenever.
    an imaginary handshake to avoid servers datagramming big returns to sleepy or non-present db workers goes like this:
    router sends a frontloaded return payload SYN of job_ID CONCATENATE query_UUID, body of return payload SYN gonna be return_payload's CRC.
    worker's SYNACK can't be anything but the return_payload expected CRC!
    router can then do a totally ordinary datagramming of return_payload;
    worker politely closes the connection as ACK, since the only data integrity dependent ACK they could send is causally accessible even without the correct transmission of the transmitted data.
        (a distracting aside: we could steganographically embed a signing key into the return_payload such that expected_CRC SIGNED stegkey allows a causally bound ACK.
        there AIN'T NO WAY we're doing that for several reasons mostly related to PAY ME.)

    we should note that the worker service must await async and possibly long operations to retrieve db values from a db key.
        however WHO CARES, it is SO MUCH MORE BLOATED for the db worker to replicate a db value in its protocol related state that this is UNIMPORTANT.
    we also might note that persisting db worker task data to the underlying db is probably fine bc its gonna be tiny (job UUID, task UUID, CRC, status) compared to the data (strings over 100 chars in length)

router server:
    accepts API queries, writes them to an intermediate queue so that we can saturate newly appearing API servers when they exist. for example we can:
        boot up a laptop. 
        load up an annotation program.
        load up our worker client. validate the annotation API, like, exists and does whatever it should.
        announce to our router server a batchsize (note: this might be a guess or might be explicit!) and a worker queue depth. e.g. batchsize 12, queue depth 17.
    once we've done this announce, the router server can balance query workload onto this laptop even if it didn't exist in our network when we first started our big data processing job!
    intriguingly, as the worker service can forecast a batchsize (implicitly, batchsize / seqlen/modelsize tradeoff) from its own configuration, 
        the routing server does not need to spend any state management on hypothetical state internal to 'noumenal' API servers, or even state internal to the worker service.
        worker services can (should (must)) reannounce their batch capacity for this protocol to make sense, 
        bc 'sequence lengths' of datasets can vary across a dataset. 
            we probably want to sort our seqlens and throw the softballs first.
            this gets big batches and big concurrency and big throughput.
            when showing off a 'ragged' or 'long tailed' dataset processing job to hypothetical stakeholders they obviously wanna see the best case (and tbh median-case) performance of a server.
    however we will still need a queue of worker services.
    FIFO? LIFO? neither! the worker services should tbh be a ~~list~~ pick2 sorted from lowest 
    value (queue depth/batchsize) to highest (queue depth/batchsize)
        this is ultimately only a heuristic btw. 
        because our routing is totally decoupled from the complexity of our tasks or the task bandwidth of the 'noumenal' API servers,
        the metric supporting our queue ordering is invalidated around 1 remote processor cycle after we sent it!
        this means that we shouldn't treat the incoming signals telling us precise queue capacities as part of our protocol state.
        we also need not expect 100% tenancy of whatever 'noumenal' api servers are in use: we might in practical terms be sharing the use of a big monolithic routed load balanced API which gave us discounted (better be discounted to 'free' 😒) 'api credits'.
            this too is not the job of the routing server: such scenarios can be handled by a configured service worker which reports 'my batchsize is 16 for all normal purposes'.
so anyways a router server does this stuff:
    accepts database worker job-UUID SYNs
        **SYNACK with job-UUID,
        accepts SYN (job-UUID, CRC,) client_query,
        SYNACK with job-UUID, CRC, task-hash
            ~~calculates task-UUIDs~~
            ~~constructs job-UUID, task-UUID header~~
            ~~SYNACKs with job-UUID, task UUID header~~
        (wants ACK so db worker won't keep requesting UUIDs forever)
        updates task explicit status
        'closes' connection (it's datagram baybee there's only a connection insofar as each side expects it)
    accepts (job-UUID, task-UUID, checksummed) headered client_query
        writes header, client_query to task queue
        calculates checksum
        SYNACKs with checksum
        (wants ACK so db worker won't keep submitting same client_query forever)
        updates task explicit status
        'closes' connection (it's datagram baybee there's only a connection insofar as each side expects it)
    polls task queue for tasks with status of unsubmitted client_query & unsubmitted return_payload
        return_payload:
        checks job-UUID, polls db worker queue (populated by db workers... announcing) for db worker with job-UUID (oh NO i just realized db workers also have to announce what jobs they can accept as returns im literally shaking rn)
        writes job-UUID, task-UUID specific header
            (datagramming happens here)
            checksum ACKs, etc.
            updates task explicit status
        client_query:
        who cares waht the UUID is??
        polls worker service queue (pick2 balancing happens here)
        writes job-UUID, task-UUID specific header
            (datagramming happens here)
            checksum ACKs, etc.
            updates task explicit status
    accepts service worker status announces 
        updates service worker ~~table~~ hashmap as usual with connection: status (batchsize normalized queue depth),
    accepts db worker announces
        updates db worker *set* of connections?
        protocol to renegotiate which db workers can accept which completed tasks is really annoying to imagine but doable
            decide by job_UUID
            refuse to cooperate with counterparties who will partition their database so that they can only ever receive job results on the exact outbound worker that sent shit off, but also will network partition their workers and have em reappear on totally different connection origins.

            **UPDATE**: is there an easier way?
            if we synthesize task_ID by hashing client_query, a failworker will discover their task results *already cached* in the routing server if they reconnect and attempt to resubmit a task.
            WOOO THAT'S AN ENTIRE NETWORK TRANSACTION WE NEVER NEED TO WRITE!!!
    
        
    



