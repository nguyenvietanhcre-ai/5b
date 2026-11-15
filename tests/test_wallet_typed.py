"""Same 32 wallet contracts with actual typed10 input and server typed mode."""
from dataclasses import replace
import test_wallet as legacy
import test_wallet_http as http


class TypedWalletPolicyTests(legacy.WalletTests):
    evidence=[]
    input_env='FIVEBMATH_QA_TYPED_INPUT_DIR'
    input_files=('questions-typed.json','sample-sets-typed.json','sources.json')
    def setUp(self):
        super().setUp()
        self.server.free_vip_pilot=replace(self.server.free_vip_pilot,response_mode='typed')


class TypedWalletHTTPTests(http.WalletHTTPTests):
    input_env='FIVEBMATH_QA_TYPED_INPUT_DIR'
    input_files=('questions-typed.json','sample-sets-typed.json','sources.json')
