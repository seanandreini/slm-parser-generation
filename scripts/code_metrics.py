import json, sys
from radon.complexity import cc_visit
from radon.raw import analyze
from radon.metrics import mi_visit

for riga in open(sys.argv[1]):
    data = json.loads(riga)
    codice = data["solution"]
    try:
        cc = sum(b.complexity for b in cc_visit(codice))
        analized = analyze(codice)
        lloc = analized.lloc
        sloc = analized.sloc
        mi = mi_visit(data["solution"], multi=True)
        
    except SyntaxError:
        mi = cc = analized.lloc = None
    print(f"{data['model']} {data['strategy']} {data['run']} - c: {cc}, lloc: {lloc}, sloc: {sloc}, MI: {mi}")