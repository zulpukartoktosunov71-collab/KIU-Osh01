import os
import sqlite3

# Папкадагы маалымат базасын (.db файлын) автоматтык түрдө табуу
db_files = [f for f in os.listdir('.') if f.endswith('.db')]

if not db_files:
    print("Ката: База файлы (.db) табылган жок!")
else:
    db_name = db_files[0]
    print(f"Базага туташуу аткарылды: {db_name}")
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Эски 1–6 курстарды өчүрүү
    cursor.execute("DELETE FROM courses;")

    # Жаңы группаларды киргизүү
    new_courses = [
        ("1-а",),
        ("1-б",),
        ("1-в",),
        ("2-а",),
        ("2-б",),
        ("3-а",),
        ("3-б",)
    ]

    cursor.executemany("INSERT INTO courses (name) VALUES (?);", new_courses)

    conn.commit()
    conn.close()

    print("ИЙГИЛИКТҮҮ: Курстар 1-а, 1-б, 1-в, 2-а, 2-б, 3-а, 3-б деп өзгөртүлдү!")