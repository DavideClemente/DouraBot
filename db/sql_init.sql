CREATE table if not exists BIRTHDAYS(
    USER_ID BIGINT PRIMARY KEY NOT NULL,
    USERNAME varchar NOT NULL,
    BIRTH_DATE varchar NOT NULL
);

CREATE TABLE if not exists BIRTHDAY_MESSAGES (
    ID serial PRIMARY KEY,
    MESSAGE varchar(2000)
);

CREATE TABLE if not exists CARDS(
    ID varchar PRIMARY KEY,
    GAME varchar,
    image bytea
);



