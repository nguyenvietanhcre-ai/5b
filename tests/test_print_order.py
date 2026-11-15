import copy,unittest,io
from pathlib import Path
from backend.practice_pdf import ordered_questions,render_pdf

class PrintOrder(unittest.TestCase):
 def test_stable_order_and_immutable_mapping(self):
  items=[{'position':i,'code':f'code-{i}','payload':{'responseMode':mode,'answer':f'answer-{i}'}} for i,mode in enumerate(['essay','typed','choice','typed','essay','choice'],1)]
  original=copy.deepcopy(items);ordered=ordered_questions(items)
  self.assertEqual([x['position'] for x in ordered],[3,6,2,4,1,5]);self.assertEqual(items,original)
  self.assertEqual({x['code']:x['payload']['answer'] for x in ordered},{x['code']:x['payload']['answer'] for x in items})
 def test_pdf_order_and_matching_solution_numbers(self):
  from pypdf import PdfReader
  items=[]
  for i,mode in enumerate(['essay','typed','choice','typed','essay','choice'],1):
   items.append({'position':i,'code':f'QA-CODE-{i}','payload':{'responseMode':mode,'topicTitle':'QA','text':f'QA Prompt {i}','prompt':[],'assets':{},'options':['1','2','3','4'] if mode=='choice' else [],'answer':f'QA Answer {i}','lesson':None,'thinking':[],'steps':[]}})
  document={'title':'QA Print order','examCode':'QA-ORDER','grade':4,'questions':items};original=copy.deepcopy(document)
  raw=render_pdf(document,include_solutions=True,frontend=Path(__file__).resolve().parents[1]/'frontend');text='\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(raw)).pages)
  positions=[3,6,2,4,1,5]
  self.assertEqual(sorted(positions,key=lambda n:text.index(f'QA Prompt {n}')),positions)
  self.assertEqual(sorted(positions,key=lambda n:text.index(f'QA Answer {n}')),positions)
  self.assertEqual(document,original)
