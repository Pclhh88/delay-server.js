"""words.json aus VAD-Segmenten (segments.json) + korrektem Skripttext.
Wörter werden innerhalb eines Segments nach Zeichenlänge verteilt (Näherung)."""
import json, re, sys
segs = json.load(open("segments.json"))
CHUNKS = [
 "Die Briten zünden fast siebentausend Tonnen Sprengstoff auf einer deutschen Insel –",
 "und die Insel bleibt einfach stehen.",
 "April 1947.", "Helgoland, mitten in der Nordsee.", "Die Bewohner sind längst weg.",
 "In den Bunkern liegen die Reste eines ganzen Krieges:", "viertausend Torpedoköpfe,",
 "neuntausend Wasserbomben,", "über neunzigtausend Granaten.",
 "Die Royal Navy verkabelt alles.", "Kilometer um Kilometer Zündkabel.",
 "Ein Schiff geht weit draußen in Stellung.", "Am 18. April, Punkt dreizehn Uhr,",
 "drückt jemand den Knopf.", "Eine der größten nicht-atomaren Explosionen der Geschichte.",
 "Als sich der Rauch verzieht, ist die Südspitze weg.", "Der Rest von Helgoland?", "Steht noch.",
 "Moment mal.", "Wie überlebt ein Felsen so etwas?", "Der Grund:",
 "Helgoland ist aus rotem Buntsandstein.", "Und der ist porös,", "voller winziger Hohlräume.",
 "Die Wucht verpufft darin, statt den Felsen zu zerreißen.",
 "Wie wenn du mit voller Kraft in ein Sofakissen schlägst statt gegen eine Glasscheibe.",
 "Die Briten geben nicht auf.", "Jahrelang werfen ihre Flugzeuge Übungsbomben auf die Insel.",
 "Bis im Dezember 1950 zwei Studenten aus Heidelberg heimlich übersetzen, die Insel besetzen und Flaggen hissen.",
 "Plötzlich redet ganz Deutschland über Helgoland.", "1952 bekommt Deutschland die Insel zurück.",
 "Und heute?", "Kommen jedes Jahr Hunderttausende Touristen.",
 "Um zollfrei Schnaps und Zigaretten zu kaufen.",
 "Auf der Insel, die nicht mal siebentausend Tonnen Sprengstoff kleingekriegt haben.",
]
assert len(CHUNKS) == len(segs), (len(CHUNKS), len(segs))
def weight(w):
    w = re.sub(r"\W", "", w)
    if w.isdigit(): return 4 * len(w)  # Jahreszahlen werden lang gesprochen
    return max(2, len(w)) + 1
words = []
for si, (seg, txt) in enumerate(zip(segs, CHUNKS)):
    ws = [w for w in txt.split() if re.search(r"\w", w)]
    tot = sum(weight(w) for w in ws); t = seg["start"]; dur = seg["end"] - seg["start"]
    for w in ws:
        d = dur * weight(w) / tot
        words.append({"w": w, "s": round(t, 3), "e": round(t + d, 3), "seg": si}); t += d
json.dump(words, open("words.json", "w"), ensure_ascii=False, indent=0)
print(len(words), "Wörter, Ende", words[-1]["e"])
