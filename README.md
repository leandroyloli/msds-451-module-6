# MSDS 451 — Checkpoint B

Estudo do bloco de crescimento: escolher ETFs e pesos, permitindo posições
negativas, com limites pelas empresas e setores dentro dos fundos.

**[Open the English report](report/checkpoint-b.html)** · [Versão aprovada em português](report/checkpoint-b-pt-br.html)

## Reproduzir

Os dados necessários estão nesta pasta. Nenhum comando normal consulta pastas
irmãs ou atualiza fontes na internet.

```powershell
cd C:/studing/msds-451-module-6
uv run --no-project --with-requirements requirements.txt python run.py --check
uv run --no-project --with-requirements requirements.txt python run.py --report-only
uv run --no-project --with-requirements requirements.txt python run.py
```

O primeiro comando verifica os resultados salvos. O segundo reconstrói figuras e
HTML. O último refaz o estudo inteiro: sete casos históricos, controle temporal,
10 mil cenários pareados de 25 anos e 50 trajetórias dinâmicas de cinco anos, com
6 mil otimizações. A execução completa leva vários minutos. `uv` instala as
dependências isoladamente; não altera o ambiente científico compartilhado.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `pipeline/` | Leitura dos dados, filtros, otimização, conta long/short, testes e relatório |
| `data/` | Preços, câmbio, liquidez, juros e metadados congelados |
| `data/holdings/` | Composição normalizada, cobertura, manifestos e arquivos originais dos emissores/CVM |
| `output/` | Pesos, operações, patrimônio, métricas, cenários e verificações |
| `figures/` | Gráficos em SVG e PNG |
| `report/` | HTML autocontido em inglês; versão aprovada em português preservada |
| `resources/` | Enunciado, bibliografia, decisões, auditorias e proveniência |

## O que os dados permitem afirmar

- Preços até 23/10/2026; meses completos até setembro de 2026.
- Experimento histórico entre julho de 2019 e setembro de 2026: inclui COVID e
  2022, mas não as crises de 2001 e 2008.
- Composições de setembro/outubro de 2026 congeladas no retrospectivo. Elas não
  certificam os limites históricos por empresa, setor, país ou moeda.
- Classes de ações são agregadas por emissor; isso não identifica todos os
  conglomerados ou grupos controladores.
- Moeda de negociação das ações subjacentes é uma aproximação; não mede toda a
  exposição cambial econômica das empresas.
- Aluguel, financiamento e margem são hipóteses explícitas. A disponibilidade
  histórica de empréstimo e as condições de uma conta real não estão comprovadas.

## Proveniência e reprodução independente

Esta é a pasta oficial do Module 6. O estudo anterior ficou preservado em
`C:/studing/msds-451-module-6-temp`. Helpers mínimos substituem o framework antigo. Os testes foram
executados novamente nesta pasta: não foram reescritos fingerprints antigos para
representar uma execução que não ocorreu. A origem dos inputs continua registrada
nos seus manifestos; caminhos de origem são documentação, não dependências.

O [manifesto de empacotamento](resources/packaging-provenance.json) identifica os
arquivos copiados. Os manifestos em `output/` identificam o código e os resultados
da nova execução. O [enunciado local](resources/assignment.md) conserva o link do
Canvas e a rubrica de cinco seções, dez pontos cada.

O [registro da troca de nomes](resources/folder-relocation.json) conserva os
caminhos anteriores. Caminhos absolutos nos registros históricos indicam a
localização na época da coleta; os comandos atuais usam esta pasta oficial.
As prévias de revisão também ficaram na pasta temporária, em `packaging-previews/`.

A verificação visual pode ser repetida no Windows, com Edge instalado:

```powershell
uv run --no-project --with playwright python pipeline/qa_html.py --root C:/studing/msds-451-module-6
```

Repositório: [leandroyloli/msds-451-module-6](https://github.com/leandroyloli/msds-451-module-6).
A solução completa é apresentada em um pull request para revisão. Não houve
merge, implantação de site ou submissão ao Canvas.
