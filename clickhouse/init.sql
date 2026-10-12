CREATE TABLE IF NOT EXISTS work_volume_record
(
    id      UUID DEFAULT generateUUIDv4(),
    factory UUID,
    start   Date,
    finish  Date,
    weight  UInt32,
    author  UInt64,
    created Date
)
ENGINE = MergeTree
ORDER BY (factory, start, finish, created);
