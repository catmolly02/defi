import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import update_resources as feed
from tagging import suggest_tags,apply_override
CAT=json.loads((ROOT/'config/catalog.json').read_text())
SRC={'id':'test','name':'Test','url':'https://example.com/rss','region':'overseas','category':'industry'}
class Tests(unittest.TestCase):
 def test_multilabel_and_keyword_boundaries(self):
  self.assertTrue({'stablecoin','cross-border','aml'}<=set(suggest_tags({'title':'Stablecoin cross-border payments KYC'},CAT)['tags']))
  self.assertNotIn('fintech-ai',suggest_tags({'title':'Retail mail'},CAT)['tags'])
 def test_source_hints_are_not_topics(self):
  self.assertEqual(suggest_tags({'title':'A bank appoints a new CFO'},CAT,['fintech-ai','security','aml'])['tags'],[])
  self.assertNotIn('sto',suggest_tags({'title':'Tokenised deposits and bank infrastructure'},CAT)['tags'])
  self.assertNotIn('online-lending',suggest_tags({'title':'Securities lending platform expands'},CAT)['tags'])
  self.assertNotIn('global-expansion',suggest_tags({'title':'Car exports hit a record'},CAT)['tags'])
 def test_review_survives_refresh(self):
  editorial=json.loads((ROOT/'config/editorial.json').read_text())
  current=json.loads((ROOT/'dist/data/resources.json').read_text())['resources']
  reviewed=next(r for r in current if r['tags'])
  incoming={**reviewed,'tags':['fintech-ai'],'auto_tags':['fintech-ai'],'tag_method':'rules-v2'}
  refreshed=feed.combine([incoming],CAT,editorial)
  self.assertEqual(refreshed[0]['tags'],reviewed['tags'])
  self.assertEqual(len(editorial['overrides']),len(current))
 def test_manual_empty_tags_and_region(self):
  self.assertEqual(apply_override({'tags':['stablecoin']},{'tags':[]},CAT)['tags'],[])
  self.assertEqual(apply_override({}, {'region':'domestic'},CAT)['region'],'domestic')
 def test_all_feed_formats(self):
  samples=[b'<rss><channel><item><title>A &amp; B</title><link>https://example.com/a</link><pubDate>20261015091000</pubDate></item></channel></rss>',b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Stablecoin</title><link rel="self" href="https://example.com/atom"/><link rel="alternate" href="https://example.com/b"/><updated>2026-10-15T00:00:00Z</updated></entry></feed>',b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"><item><title>BIS</title><link>https://example.com/c</link></item></rdf:RDF>']
  rows=[feed.parse_feed(s,SRC,CAT)[0] for s in samples]
  self.assertEqual(rows[0]['title'],'A & B');self.assertEqual(rows[0]['published_at'],'2026-10-15T00:10:00+00:00');self.assertEqual(rows[1]['url'],'https://example.com/b');self.assertIsNone(rows[2]['published_at'])
 def test_canonical_url(self):
  self.assertEqual(feed.resource_id('https://example.com/a?id=1&utm_source=rss#x'),feed.resource_id('https://example.com/a?id=1'))
  self.assertNotEqual(feed.resource_id('https://example.com/a?id=1'),feed.resource_id('https://example.com/a?id=2'))
 def test_override_and_manual_registration(self):
  row=feed.parse_feed(b'<rss><channel><item><title>Stablecoin</title><link>https://example.com/a</link></item></channel></rss>',SRC,CAT)[0]
  result=feed.combine([row,row],CAT,{'overrides':{row['id']:{'tags':['sto'],'region':'domestic','summary':'human note'}},'manual_resources':[{'title':'My report','url':'https://example.com/report','tags':['security'],'category':'research'}]})
  self.assertEqual(len(result),2);r=next(r for r in result if r['id']==row['id']);self.assertEqual(r['tags'],['sto']);self.assertEqual(r['region'],'domestic');self.assertEqual(r['summary'],'human note')
 def test_unsafe_urls(self):
  for u in ['javascript:alert(1)','file:///etc/passwd','https://name:pass@example.com/a']:
   with self.assertRaises(ValueError):feed.canonical_url(u)
  self.assertEqual(feed.combine([],CAT,{'overrides':{},'manual_resources':[{'title':'bad','url':'javascript:alert(1)'}]}),[])
if __name__=='__main__':unittest.main()
