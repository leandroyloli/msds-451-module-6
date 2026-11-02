# Composições v2 — fontes, cobertura e limites

Base congelada: 46 dos 61 candidatos possuem arquivo completo recuperado de
emissor ou regulador; 68.260 posições normalizadas. Todos os 61 permanecem em
`data/v2/holdings/coverage.csv`, inclusive indisponíveis. `manifest.json` guarda
origens, datas e hashes. A existência de arquivo completo não significa que toda
posição interna tenha classificação ou expansão completa.

## Fontes primárias

- Vanguard: API pública de posições identificada no JavaScript do próprio
  emissor, endpoint `advisors.vanguard.com/investments/products/api/funds/{id}/holdings/latest`.
  Fotografias em 30/09/2026, preservadas em JSON.
- iShares/BlackRock: CSVs completos nos endpoints `latest-holdings.csv` e export
  brasileiro. Fotografias em 30/10/2026, preservadas em CSV.
- SPY: XLSX oficial State Street, convertido sem modificar os dados; 29/10/2026.
- Fundos B3: arquivo oficial CVM CDA setembro/2026,
  `https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/cda_fi_202609.zip`.
  O ZIP e as linhas por CNPJ permanecem na pasta de dados. Inclui DIVO11 e
  diversos outros fundos locais. BOVA11 utiliza a fotografia mais recente do
  emissor BlackRock.

## Transformações

Pesos são frações do patrimônio. Para CSVs iShares, valores de mercado completos
reconstroem pesos com mais precisão que percentuais publicados arredondados.
Não são inventadas posições ausentes. Vanguard tinha uma seção duplicada de
reservas em fundos; ela foi excluída para não contar o mesmo caixa duas vezes.

Classes de ações são agrupadas por nome normalizado do emissor. Classificações
e moedas são transferidas entre fontes apenas por identificadores ou combinações
exatas não conflitantes de título, nome e país. O mapa de subindústria para setor
amplo exige concordância das posições primárias. A classificação portuguesa
`Renda Variável` foi normalizada para `Equity`; isso evita excluir falsamente
BOVA11 das métricas de cobertura de ações.

Moeda é a moeda de negociação dos títulos subjacentes quando identificável,
não a moeda das receitas das empresas nem hedge cambial econômico. Valores
desconhecidos ficam vazios e devem consumir o orçamento de exposição desconhecida.

IVVB11 e WRLD11 têm posições em outros fundos expandidas recursivamente com
fotografias atuais de IVV/VT. São datas combinadas explicitamente qualificadas.
NASD11 e VWRA11 ainda possuem posições opacas não expandidas; o arquivo da CVM
ser completo não autoriza presumir cobertura econômica completa.

## Limitações materiais

Não foram recuperadas carteiras históricas completas de 2019–2026. Aplicar esta
matriz a retornos antigos é um experimento retrospectivo de composição congelada,
não uma certificação causal dos limites no passado. País de SPY não foi recuperado
adequadamente; lacunas de indústria/moeda continuam mensuradas por fundo.
Derivativos e posições em caixa exigem cuidado: pesos por valor de mercado não
substituem análise completa de nocional/delta. Nenhuma destas fontes comprova
disponibilidade histórica de empréstimo para vender ETFs a descoberto.

## Verificação final

61 linhas únicas de cobertura, 68.260 posições com pesos numéricos e identificador
de emissor; hashes de holdings/coverage conferidos com o manifesto. Dados finais
publicados atomicamente, sem alterações em arquivos v1.
