# Inventário de runtime e prontidão — 05/10/2026

Este registro diferencia disponibilidade de fonte/artefato e dados históricos de condições físicas atuais. `experiment.v1.json` mantém prontidão blocked e campos atuais nulos. Não houve nova sessão em aparelho nesta revisão.

| Dado | Evidência existente | Uso permitido / pendência |
| --- | --- | --- |
| Modelo | EfficientDet-Lite0, 4.563.519 bytes; SHA-256 2e04c53bfeac0ac2a30c057c7e2a777594ce39baaac35a92f74fb1e8c4fc4e0b, manifesto IA/mobile | Identidade do baseline; não mede precisão em sala |
| Aplicativo integrado | Mobile dev 2f7be1c0fd4e481d2e6864d0c89edfb606087a6a após merge #19; Front 1749f14, Back 5c047de, IA ad6cbdd | Base antes da REN-68; registrar o SHA final dos novos MRs no checkpoint |
| APK visual anterior | Profile/dev 04028c1, SHA-256 bd0ed1629a25c31b52a5924f575ccca04fbb9d7c5210fe6bf9b713d48b754fb9; calibração desabilitada | Avaliação visual preparada, não APK opt-in para coleta |
| Hardware/Android históricos | REN-29, 21/08/2026: POCO X5 Pro 5G, Android 14/API34, Profile/dev, 4 threads, 12fps | Recapturar inventário da unidade antes do novo ensaio |
| Hardware/Android do piloto | `ren37-smoke-20260916-09.start.json`: modelo 22101320G, Android14/API34, 16/09/2026 | Não transplantar como condição atual |
| Bateria do piloto | 27%, estado Android2 (carregando), temperatura inicial31°C | Não prova consumo; repetir sem carregamento e com estados registrados |
| RAM da unidade atual | Não capturada nesta revisão | null; variantes comerciais não identificam a unidade |
| Fingerprint SHA-256 atual | Não capturado nesta revisão | null; obter digest, não divulgar fingerprint bruto |
| Versão/commit do piloto | Sidecar histórico sem buildIdentity | Não inventar; classificar pilot/legacy, sem manifesto final retroativo |
| Bateria/temperatura/estado térmico atuais | Não capturados nesta revisão | null; capturar para cada sessão/build |
| Pipeline / metas | Políticas e marcos instrumentados no código, dados históricos limitados | Não converter médias de REN-29 em p95/TTS; separar relógios |
| Corpus/avaliação final | Não executados nesta revisão | Bloqueados pela coleta/independência/anotação e critérios restantes |

A ausência de campos é uma pendência explícita, não um valor zero. Os recibos do APK, os 31 artefatos originais e a nova reanálise do piloto ficam no workspace de auditoria e nos checkpoints Linear. Logs/versões dos MRs demonstram testes de software, sem atribuir medições físicas atuais a esses testes.
