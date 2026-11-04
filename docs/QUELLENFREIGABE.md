# Aktueller Zugriffsbefund und konkrete Freigabeanfragen

Geprüft am 4. November 2026. Öffentliche Sichtbarkeit und Zustimmung des Archivbetreibers heben ausdrückliche Bedingungen des Quellendienstes nicht auf.

## FamilyTreeDNA

Offizielle Bedingungen: https://www.familytreedna.com/legal/terms-of-service

Der Inhalt wird auf dieser öffentlichen Seite dynamisch eingebunden. Die Seite zeigt unter anderem folgende ausdrückliche Einschränkungen:

> use any robot, spider, or other devices or any other means to access, scrape, or crawl any pages or other services on the Website for any purpose, including monitoring or copying any of the material on the Website.

> Except with our express prior written consent or as otherwise permitted under these Terms, you must not reproduce, distribute, modify, create derivative works of, publicly display, publicly perform, republish, download, store, or transmit any of the material on our Website nor systematically download any data or material from or through the Website for any purpose, such as to make or populate another database.

Eine permissive robots.txt allein ist deshalb keine ausreichende Freigabe. Der Dienst prüft ab jetzt **vor jedem Ergebnisabruf** sowohl `automated_access_allowed` als auch `access_permission_url`. Zusätzlich bleiben `publication_allowed` und `permission_url` für die Übernahme relevant. Ohne belegte Freigabe wird nur der Status `restricted` protokolliert; es erfolgt kein Ergebnisabruf. Diese Felder dürfen nicht allein wegen der öffentlichen Sichtbarkeit auf freigegeben gesetzt werden.

Vorlage für eine Anfrage durch den Projektbetreiber; bisher nicht versendet:

> Subject: Permission request: limited public Y-DNA project synchronization
>
> I maintain the non-commercial Egyptian Y-DNA archive at https://egyptydna.github.io/Egypt-Y-DNA/ . Please confirm whether we may automatically retrieve publicly shared Y-DNA group-project results with Egyptian paternal origin once every twelve hours and republish the public kit ID, public ancestor/name where permitted, paternal origin, haplogroup, explicitly published test type, SNP path and STR values with source attribution. We will use no logins or administrator data, respect agreed rate limits, preserve provenance, and implement opt-outs and removal requests. If scraping public pages is not permitted, can you provide or approve a public API or export/feed for this purpose? Please specify the permitted fields and republication conditions.

## YFull

**Ergänzung:** Die offizielle Quelle [YFullTeam/YTree](https://github.com/YFullTeam/YTree)
stellt einen CC-BY-4.0-lizenzierten JSON-Baum bereit. Dafür ist jetzt ein separater
GitHub-Adapter implementiert. Er umgeht keine Website-Sperre und liefert keine
individuellen Proben. Details: [GitHub-Datenquellen](GITHUB-DATENQUELLEN.md).

Aktuelle robots.txt: https://www.yfull.com/robots.txt

```text
User-agent: *
Disallow: /
Crawl-delay: 10
```

Der Dienst gibt sich nicht als Googlebot, Bingbot oder OAI-SearchBot aus, um anderslautende Regeln auszunutzen. Die sichtbare CC-BY-Kennzeichnung eines YTree und die Kennzeichnung `New` sind keine Aufhebung der allgemeinen Crawl-Sperre.

Vorlage für eine Anfrage durch den Projektbetreiber; bisher nicht versendet:

> Subject: Authorized YTree update feed for Egyptian samples
>
> I maintain the non-commercial Egyptian Y-DNA archive at https://egyptydna.github.io/Egypt-Y-DNA/ . We would like to synchronize publicly shared Egyptian paternal-origin samples once every twelve hours, including YFull ID, current terminal branch, verified path/aliases, public region and the published New flag, with attribution and opt-out support. We distinguish modern customers, study samples and ancient samples, and do not infer Big Y from a YFull ID. Your robots.txt disallows general crawling; we will respect that. Is there an authorized API, public export or feed, and what are its automated-access and republication conditions?

Der vorhandene erlaubte Exportweg erhält `is_new` und `tree_version`. Neue und geänderte Ergebnisse werden weiterhin anhand stabiler IDs und des Inhalts erkannt: Eine verschwundene `New`-Markierung darf kein Profil entfernen; ein verschobenes älteres Sample muss ebenfalls aktualisiert werden. Ohne erlaubten individuellen Feed gibt es keine automatische Aktualisierung einzelner YFull-Proben. Die lizenzierte GitHub-Topologie wird unabhängig davon abgeglichen.

## Sofortstart und Zeitplan

Der Workflow wird auf eine gezielte Änderung seiner Datei oder von `sync/**` im Standardbranch reagieren. Nach Freigabe und Merge dieser Korrektur wird damit ein erster Schreib-/Statuslauf eingereiht, ohne auf die nächste Cron-Zeit oder einen manuellen Start zu warten. Der Zeitplan bleibt **00:23 und 12:23 UTC**. Eine GitHub-Actions-/Pages-Störung kann auch den ersten Lauf und die Zeitpläne verzögern. Das ist kein garantierter Start zu einer festen Sekunde.

Ein erfolgreicher technischer Lauf ohne freigegebene Datenquelle ist **kein erfolgreicher Datenimport**. Der Bericht unterscheidet `restricted`, `disabled` und `ok` und nennt `sources_checked_successfully`. Nach Merge der GitHub-Erweiterung ist `yfull-github` eine aktivierte lizenzierte Baumquelle; neue individuelle Tester sind damit nicht verbunden. Bestehende Archivdaten bleiben erhalten.
