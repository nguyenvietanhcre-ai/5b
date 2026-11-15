"""Explicit native localhost test mode; never a production/Worker source toggle.

Does not seed or import question tables, alter existing balances, or approve a
commercial play policy. It supplies separate synthetic providers in memory.
"""
from http.server import HTTPServer
from urllib.parse import urlsplit
from . import platform_api as api
from .group_games import GroupGames
from .group_game_bots import BotGroupGames


class LocalTestGroupGames(BotGroupGames):
    def enabled(self):
        return self.source.qa_only is True

    def catalogue(self, grade):
        value=super().catalogue(grade)
        return {**value,'localTest':True,'sourceStatus':'local-test','policyStatus':'pending-commercial',
                'notice':'Bộ câu test riêng · Chưa duyệt học liệu để dùng chính thức.',
                'limitsNotice':'Chế độ thử cục bộ chưa áp chính sách lượt chơi chung cho ba game.'}


class NativeLocalTestGames:
    def __init__(self,external_ports):
        ports=frozenset(external_ports)
        if not ports or len(ports)>4 or any(type(p) is not int or not 1024<=p<=65535 for p in ports):
            raise ValueError('Explicit native localhost external ports required')
        self.external_ports=ports
        # These fixture modules remain excluded from Worker production bundles.
        from .arena_qa_source import ArenaQAQuestionSource,ArenaBotQAQuestionSource
        from .group_games_qa import synthetic_source
        self.arena=ArenaQAQuestionSource();self.bot=ArenaBotQAQuestionSource()
        self.group_games=LocalTestGroupGames(synthetic_source())

    def allowed(self,handler):
        server=handler.server
        if not isinstance(server,HTTPServer) or getattr(server,'native_python_backend',False) is not True:
            return False
        if getattr(server,'local_test_games',None) is not self:
            return False
        try:
            host=urlsplit('//'+handler.headers.get('Host',''))
            if host.username or host.password or host.path or host.query or host.fragment:
                return False
            if host.hostname not in ('localhost','127.0.0.1','::1') or host.port not in self.external_ports:
                return False
            public=api.public_origin()
            if public and urlsplit(public).hostname not in ('localhost','127.0.0.1','::1'):
                return False
        except (ValueError,AttributeError):
            return False
        return True

    def metadata(self,kind):
        source=self.bot if kind=='bot' else self.arena
        label=('Luyện với bot · Dữ liệu test cục bộ · Không tính kinh nghiệm/xếp hạng' if kind=='bot'
               else 'Bộ câu test riêng cho Đấu trí · Thử cục bộ · Chưa duyệt học liệu')
        return {**source.metadata(),'qaOnly':False,'localTest':True,'status':'local-test','label':label,
                'policyStatus':'existing-duel-limits-unchanged' if kind=='pvp' else 'existing-bot-limits-unchanged'}
