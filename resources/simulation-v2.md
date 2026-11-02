# Monte Carlo da versão comprada/vendida

O módulo `pipeline/simulation_v2.py` escreve somente em `output/v2`. Os arquivos
da primeira versão ficam preservados.

## Experimento 1: incerteza do processo líquido

- Entradas: `Long-short`, `Somente comprado`, `Pesos iguais`, `VT`, `RF` e `FX`
  em `output/v2/daily_returns.csv`.
- Os retornos diários são compostos geometricamente em meses completos. Não se
  descontam novamente custos já presentes nesses retornos líquidos.
- Bootstrap estacionário circular pareado: todos os ETFs/estratégias, caixa e
  câmbio recebem exatamente o mesmo índice sorteado em cada mês. O comprimento
  esperado do bloco é seis meses; seed fixo.
- 10.000 trajetórias com horizonte de 300 meses (25 anos). Percentis são cenários
  condicionais, não probabilidades futuras calibradas.
- Intervalos pareados de 95% usam 2.000 reamostragens do horizonte observado,
  separadamente com blocos esperados de 3, 6 e 12 meses. Não se escolhe o bloco
  cujo resultado for mais favorável.
- Sharpe é mensal, anualizado por raiz de 12. Drawdown é observado nos
  fechamentos mensais; pode ser menor que a perda intramês. BRL é conversão
  conjunta nominal, sem chamar o caixa em USD de ativo livre de risco em BRL.

Esse replay mede a variabilidade do processo líquido histórico; ele não refaz
o otimizador a cada passo sintético.

## Experimento 2: algoritmo reestimado em dados gerados

- Fixar o universo que passa pelo histórico/liquidez em junho de 2019,
  intersectado com a cobertura atual completa de composição.
- Gerar vetores conjuntos de retornos de ETFs, caixa e FX em blocos. O
  reservatório começa em julho de 2014, inclui COVID e termina em setembro de
  2026, sujeito à interseção efetivamente disponível.
- Gerar 50 trajetórias. Cada uma tem 60 meses de treinamento e 60 de teste.
- Reestimar os dois modelos a cada mês de teste: comprado/vendido e somente
  comprado. Isso dá 6.000 otimizações quando não há insolvências.
- O retorno de manutenção nunca entra em sua própria janela de estimação.
  A taxa de caixa do mês é uma proxy derivada do último DGS3MO conhecido antes
  daquele mês no arquivo de origem.
- Usar `model_v2.Optimizer`, `closest_band` e `execution_v2.Account`, com as
  mesmas restrições, bandas, negociação, gestão, aluguel e financiamento.
- Conta separa posições assinadas, caixa, garantia e dívida. Retornos ajustados
  já incluem distribuições: não se cobra o dividendo outra vez na ponta vendida.
- Chamadas de margem detectadas no fechamento anterior são liquidadas na
  próxima execução mensal; isso é uma aproximação, não uma simulação diária de
  corretora. Trajetórias insolventes mantêm seu déficit e nunca são descartadas.
  Métricas sem definição após insolvência ficam ausentes com contagem explícita.
- Falha do solver interrompe o estudo, em vez de remover silenciosamente a
  trajetória. Hashes do modelo e da contabilidade precisam permanecer iguais
  durante toda a execução.

## Limitação que deve ficar visível no HTML

**A matriz de empresas, setores, países e moedas é uma fotografia atual dos
emissores. Congelar essa fotografia sobre preços antigos é um cenário
retrospectivo. Não é uma validação causal dos limites históricos de composição.**

Os testes de preços/estimativas mantêm ordem temporal, mas isso não remove a
informação posterior embutida na matriz congelada e na cobertura atual do
universo. Para afirmar execução histórica fiel desses limites seria necessária
uma série de carteiras completas dos emissores conhecida em cada data.

Com 50 trajetórias dinâmicas, uma proporção tem resolução de dois pontos
percentuais e erro-padrão Monte Carlo máximo de aproximadamente 7,1 pontos.
Isso é adicional à incerteza de dados, retornos, aluguel e regimes futuros.

## Saídas

`mc_summary.json`, `mc_percentiles.csv`, `mc_intervals.csv`,
`mc_terminal_samples.csv`, `mc_monthly_returns.csv`, `mc_verification.json`;
`mc_dynamic_summary.json`, `mc_dynamic_paths.csv`, `mc_dynamic_trace.csv`,
`mc_dynamic_reservoir.csv`, `mc_dynamic_rf_source.json` e
`mc_dynamic_verification.json`.
