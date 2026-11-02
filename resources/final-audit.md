# Revisão final e nova execução independente

## Evidência anterior à separação de pastas

Uma revisão independente, somente leitura, do estudo de origem em
`C:/studing/msds-451-module-6` encontrou:

- Erro máximo de reconstrução independente do patrimônio: aproximadamente
  1,33 × 10⁻¹⁵ por unidade de capital inicial.
- Reconciliação dos retornos compostos, volatilidades e limites assinados dos
  sete casos, em todas as decisões mensais.
- Execuções entre um e cinco dias após o sinal, com cotação observada em todas
  as posições não nulas.
- Reconciliação da conversão para BRL e dos fingerprints do Monte Carlo.
- Alfa de regressão long/short de aproximadamente 0,5306 ponto percentual ao ano,
  beta 0,8520; a regra apenas comprada teve alfa 0,6115 e beta 0,8502.
- A carteira atual tinha nove posições compradas, embora posições negativas
  fossem permitidas. Não foram impostas vendas para alterar o resultado.

Esses pontos documentam a origem. Não substituem a reexecução desta pasta.

## Evidência desta pasta

A separação de pastas muda os caminhos e o código-fonte dos helpers. Por isso os
resultados foram executados novamente, sem alterar fingerprints de saídas antigas.

O registro autoritativo da nova execução é `../output/verification.json`, junto
com `../output/mc_dynamic_verification.json`, `../output/artifact_manifest.json`
e `../output/environment.json`. As verificações independentes reconstroem o P&L
sem recorrer à classe de contabilidade usada no backtest.

As verificações numéricas não resolvem a principal limitação científica:
composições de 2026 foram congeladas no experimento retrospectivo. Não há
certificação dos limites por empresa/setor com as composições vigentes no passado.
