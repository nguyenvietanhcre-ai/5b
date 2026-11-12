"""Create the first administrator locally without public staff registration."""
import argparse
import getpass
from pathlib import Path
from .database import initialize
from .platform_api import connect


def main():
    parser = argparse.ArgumentParser(description='Tạo admin đầu tiên của 5BMath')
    parser.add_argument('--database', type=Path, default=Path('work/database/5bmath-demo.sqlite3'))
    parser.add_argument('--login', default='admin')
    parser.add_argument('--name', default='Quản trị 5BMath')
    args = parser.parse_args()
    initialize(args.database)
    with connect(args.database) as db:
        if db.execute("SELECT 1 FROM staff_users WHERE role='admin'").fetchone():
            parser.exit(1, 'Đã có admin. Đăng nhập trang Quản trị để cấp tài khoản tiếp theo.\n')
    password = getpass.getpass('Mật khẩu admin (ít nhất 6 ký tự): ')
    if password != getpass.getpass('Nhập lại mật khẩu: '):
        parser.exit(1, 'Hai mật khẩu chưa khớp.\n')
    from .staff_api import create_first_admin
    create_first_admin(args.database, args.login, args.name, password)
    print('Đã tạo admin. Mở /quan-tri/ để đăng nhập.')


if __name__ == '__main__':
    main()
