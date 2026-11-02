# Fonte histórica da coleta

`holdings_v2.py` é uma cópia preservada do programa exploratório que recuperou e
normalizou as composições do estudo de origem. Não é chamado pelo `run.py` e seus
caminhos originais não foram adaptados para fingir uma coleta nova.

O processo consultou páginas dos emissores, arquivos completos CSV/JSON/XLSX,
dados públicos da CVM e intermediários de normalização; cruzou identificadores
de títulos para completar classificações e documentou o que continuou ausente.
Algumas etapas exploratórias produziram arquivos `stage`, HTML e JavaScript no
workspace original. Este arquivo isolado não promete reconstruir toda a coleta
ou reproduzir uma nova fotografia das fontes online.

Os 46 arquivos brutos efetivamente referenciados no manifesto final estão em
`../../data/holdings/`; os hashes desses arquivos foram conferidos após a cópia.
`../../data/holdings/manifest.json` descreve fontes e transformações. Os dados
normalizados congelados são suficientes para refazer todo o estudo nesta pasta,
sem rede nem dependência do workspace de origem.

Origem preservada: `C:/studing/msds-451-module-6/pipeline/holdings_v2.py`.
