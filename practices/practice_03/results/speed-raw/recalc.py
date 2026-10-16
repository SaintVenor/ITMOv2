import json,sys,statistics,os
d=sys.argv[1]; names=sys.argv[2:]
rates={}
print(f"{'файл':<32}{'load_s':>9}{'total_s':>9}{'eval_count':>11}{'eval_s':>10}{'tok/s':>8}")
for n in names:
    raw=open(os.path.join(d,n)).read().strip().splitlines()
    o=json.loads(raw[-1])
    if "error" in o: print(f"{n:<32}ОШИБКА: {o['error']}"); continue
    ec,ed=o["eval_count"],o["eval_duration"]; r=ec/(ed/1e9); rates[n]=r
    print(f"{n:<32}{o['load_duration']/1e9:9.4f}{o['total_duration']/1e9:9.4f}{ec:11d}{ed/1e9:10.6f}{r:8.2f}")
print()
for label,keys in [("Повторы warm1, warm2, warm3_fix (без первого прогретого warm0)",["ollama_gen_warm1.json","ollama_gen_warm2.json","ollama_gen_warm3_fix.json"]),
                   ("Как в старом отчёте: warm0, warm1, warm2",["ollama_gen_warm0.json","ollama_gen_warm1.json","ollama_gen_warm2.json"])]:
    v=[rates[k] for k in keys if k in rates]
    print(f"{label}: медиана {statistics.median(v):.2f} tok/s (значения: {', '.join(f'{x:.2f}' for x in v)})")
