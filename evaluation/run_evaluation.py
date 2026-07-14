from pathlib import Path
import json,csv,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from taura.intent_classifier import classify
from taura.rag_retriever import RagRetriever
from taura.entity_extractor import extract
DATA=ROOT/"evaluation"/"multilingual_100_queries.json"; OUT=ROOT/"evaluation"/"results"
def main():
 rows=json.loads(DATA.read_text(encoding="utf-8")); r=RagRetriever(); results=[]
 for x in rows:
  c=classify(x["query"]); intent=c.intent.value if hasattr(c.intent,"value") else str(c.intent)
  ents=extract(x["query"]); rec=(r.find_price(ents) if intent=="market_price" else r.find_climate_alert(ents) if intent=="climate_alert" else (r.find_financial_products()[0] if r.find_financial_products() else None) if intent=="financial_query" else None)
  st=getattr(rec,"source_type",None) if rec else None
  results.append({**x,"predicted_intent":intent,"retrieved_source_type":st,"intent_correct":intent==x["expected_intent"],"source_correct":x["expected_source_type"] is None or st==x["expected_source_type"]})
 OUT.mkdir(exist_ok=True)
 n=len(results); ia=sum(z["intent_correct"] for z in results)/n
 cases=[z for z in results if z["expected_source_type"]]; ra=sum(z["source_correct"] for z in cases)/len(cases)
 langs={k:sum(z["intent_correct"] for z in results if z["language"]==k)/len([z for z in results if z["language"]==k]) for k in sorted(set(z["language"] for z in results))}
 summary={"queries":n,"intent_accuracy":ia,"retrieval_accuracy":ra,"language_intent_accuracy":langs,"max_language_gap":max(langs.values())-min(langs.values())}
 (OUT/"evaluation_results.json").write_text(json.dumps({"summary":summary,"results":results},indent=2,ensure_ascii=False),encoding="utf-8")
 with (OUT/"evaluation_results.csv").open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=results[0].keys());w.writeheader();w.writerows(results)
 (OUT/"EVALUATION_RESULTS.md").write_text("# Taura AI 100-Query Evaluation Results\n\n"+ "\n".join([f"- Queries: **{n}**",f"- Intent accuracy: **{ia:.1%}**",f"- Retrieval accuracy: **{ra:.1%}**",f"- Maximum language gap: **{summary['max_language_gap']:.1%}**"]+[f"- {k} intent accuracy: **{v:.1%}**" for k,v in langs.items()]),encoding="utf-8")
 print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
