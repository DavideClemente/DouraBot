

def get_next_user_number(db):
    with db.cursor() as cursor:
        cursor.execute(
            'SELECT IFNULL(MAX(user_number), 0) + 1 AS next_user_number FROM DISCORD_USERS')
        result = cursor.fetchone()
        return result[0] if result else 1


def insert_user(db, id, username, user_number):
    with db.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO DISCORD_USERS (user_id, user_number, username, join_date, TIMES_LEFT) 
            VALUES (%s, %s, %s, NOW(), 0)
            ''',
            (id, user_number, username)
        )
    db.commit()
