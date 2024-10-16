from itertools import product
from tabulate import tabulate
from gurobipy import Model, GRB, GurobiError
from itertools import chain

def gerar_padroes(comprimento_barra, comprimentos_itens):
    max_itens = [comprimento_barra // comprimento for comprimento in comprimentos_itens]
    padroes = []
    for combinacao in product(*[range(max + 1) for max in max_itens]):
        comprimento_ocupado = sum(combinacao[i] * comprimentos_itens[i] for i in range(len(comprimentos_itens)))
        if comprimento_ocupado <= comprimento_barra:
            padroes.append(combinacao)
    return padroes

def calcular_perda(padroes, comprimento_barra, comprimentos_itens):
    perdas = []
    for padrao in padroes:
        comprimento_ocupado = sum(padrao[i] * comprimentos_itens[i] for i in range(len(comprimentos_itens)))
        perda = comprimento_barra - comprimento_ocupado
        perdas.append(perda)
    padroes_filtrados = [padrao for padrao in padroes if any(x > 0 for x in padrao)]
    perdas_filtradas = [perda for padrao, perda in zip(padroes, perdas) if any(x > 0 for x in padrao)]
    return padroes_filtrados, perdas_filtradas

def obter_input_inteiro(prompt):
    while True:
        try:
            valor = input(prompt)
            if valor.lower() == 'cancelar':
                return 'cancelar'
            return int(valor)
        except ValueError:
            print("Entrada inválida. Tente novamente ou digite 'cancelar' para sair.")

def gerar_tabela_padroes(padroes, perdas):
    tabela = [(str(padrao), perda) for padrao, perda in zip(padroes, perdas)]
    headers = ["Padrão de Corte", "Perda"]
    return tabela, headers

def funcao_objetivo_e_restricoes(padroes, perdas, demandas):
    num_padroes = len(padroes)
    num_itens = len(demandas)
    
    funcao_objetivo = "Minimizar: " + " + ".join([f"{perdas[i]} * x{i+1}" for i in range(num_padroes)])
    restricoes = []
    
    for j in range(num_itens):
        restricao =  " + ".join([f"{padroes[i][j]} * x{i+1}" for i in range(num_padroes)]) + f" >= {demandas[j]}"
        restricoes.append(restricao)

    restricao_non_negatividade = ", ".join([f"x{i+1}" for i in range(num_padroes)]) + " >= 0"
    restricoes.append(restricao_non_negatividade)

    return funcao_objetivo, restricoes

def algoritmo_unidimensional():
    while True:
        comprimento_barra = obter_input_inteiro("Digite o comprimento total da barra: ")
        if comprimento_barra == 'cancelar':
            return 'cancelar'
        
        n_itens = obter_input_inteiro("Digite o número de tipos de itens: ")
        if n_itens == 'cancelar':
            return 'cancelar'
        
        demandas = []
        comprimentos_itens = []

        i = 0
        while i < n_itens:
            print(f"\nItem {i+1}:")
            demanda = obter_input_inteiro(f"Digite a demanda do item {i+1}: ")
            if demanda == 'cancelar':
                return 'cancelar'
           
            comprimento_item = obter_input_inteiro(f"Digite o comprimento do item {i+1}: ")
            if comprimento_item == 'cancelar':
                return 'cancelar'
            
            demandas.append(demanda)
            comprimentos_itens.append(comprimento_item)
            i += 1

        padroes = gerar_padroes(comprimento_barra, comprimentos_itens)
        padroes_filtrados, perdas_filtradas = calcular_perda(padroes, comprimento_barra, comprimentos_itens)
        return comprimento_barra, demandas, comprimentos_itens, padroes_filtrados, perdas_filtradas

def filtrar_padroes_homogeneos(padroes):
    padroes_homogeneos = []
    for padrao in padroes:
        non_zero_count = sum(1 for x in padrao if x > 0)
        if non_zero_count == 1:
            padroes_homogeneos.append(padrao)
    return padroes_homogeneos

def selecionar_melhor_padrao_homogeneo(padroes_homogeneos, comprimento_barra, comprimentos_itens):
    melhores_padroes = []
    melhores_perdas = []
    
    for j in range(len(comprimentos_itens)):
        melhor_padrao = None
        max_cortes = 0
        melhor_perda = None
        
        for padrao in padroes_homogeneos:
            if padrao[j] > max_cortes:
                melhor_padrao = padrao
                max_cortes = padrao[j]
                comprimento_ocupado = padrao[j] * comprimentos_itens[j]
                melhor_perda = comprimento_barra - comprimento_ocupado
        
        if melhor_padrao:
            melhores_padroes.append(melhor_padrao)
            melhores_perdas.append(melhor_perda)
    
    return melhores_padroes, melhores_perdas

def resolver_problema_mestre_restrito(melhores_padroes, melhores_perdas, demandas):
    try:
        num_padroes = len(melhores_padroes)
        restricoes = []
        for j in range(len(demandas)):
            restricao = " + ".join([f"{melhores_padroes[i][j]} * y{i+1}" for i in range(num_padroes)]) + f" >= {demandas[j]}"
            restricoes.append(restricao)

        for restricao in restricoes:
            modelo = Model("Problema Mestre Restrito")
        modelo.setParam('OutputFlag', 0)
        y = modelo.addVars(num_padroes, lb=0, vtype=GRB.CONTINUOUS, name="y")
        modelo.setObjective(sum(y[i] for i in range(num_padroes)), GRB.MINIMIZE)
        for j in range(len(demandas)):
            modelo.addConstr(sum(melhores_padroes[i][j] * y[i] for i in range(num_padroes)) >= demandas[j], name=f"demanda_{j}")
        modelo.addConstrs((y[i] >= 0 for i in range(num_padroes)), name="non_negativity")
        modelo.optimize()
        if modelo.status == GRB.OPTIMAL:
            return modelo
        else:
            return None
    except GurobiError as e:
        print(f"Erro Gurobi: {e}")
    except Exception as e:
        print(f"Erro: {e}")

def resolver_subproblema_maximizacao(comprimento_barra, comprimentos_itens, dual_values):
    try:
        num_itens = len(comprimentos_itens)
        modelo = Model("Subproblema de Maximização")
        modelo.setParam('OutputFlag', 0)
        x = modelo.addVars(num_itens, lb=0, vtype=GRB.INTEGER, name="x")
        modelo.setObjective(sum(dual_values[i] * x[i] for i in range(num_itens)), GRB.MAXIMIZE)
        modelo.addConstr(sum(comprimentos_itens[i] * x[i] for i in range(num_itens)) <= comprimento_barra, name="comprimento")
        modelo.addConstrs((x[i] >= 0 for i in range(num_itens)), name="non_negativity")
        modelo.optimize()
        if modelo.status == GRB.OPTIMAL:
            return modelo
        else:
            return None
    except GurobiError as e:
        print(f"Erro Gurobi: {e}")
        return None
    except Exception as e:
        print(f"Erro: {e}")
        return None

def resolver_problema_mestre_restrito_novo(melhores_padroes, melhores_perdas, demandas_residuais, comprimentos_itens, comprimento_barra):
    custo_relativo = -1
    while custo_relativo < 0:
        modelo = resolver_problema_mestre_restrito(melhores_padroes, melhores_perdas, demandas_residuais)
        if modelo:
            dual_values = obter_valores_duais(modelo, demandas_residuais)
            subproblema_modelo = resolver_subproblema_maximizacao(comprimento_barra, comprimentos_itens, dual_values)
            if subproblema_modelo:
                custo_relativo = verificar_custo_relativo(subproblema_modelo)
                if custo_relativo < 0:
                    nova_coluna = [int(var.X) for var in subproblema_modelo.getVars()]
                    melhores_padroes.append(nova_coluna)
                    comprimento_ocupado = sum(nova_coluna[i] * comprimentos_itens[i] for i in range(len(comprimentos_itens)))
                    nova_perda = comprimento_barra - comprimento_ocupado
                    melhores_perdas.append(nova_perda)
            else:
                print("Falha ao resolver o subproblema de maximização.")
                break
        else:
            print("Falha ao resolver o problema mestre restrito.")
            break
    associar_padroes_solucao_otima(modelo, melhores_padroes)
    if custo_relativo >= 0:
        solucao_truncada_y, demandas_residuais = truncar_solucao(modelo, melhores_padroes, demandas_residuais)
        if all(y < 1 for y in solucao_truncada_y):
                
                padroes_ffd, perdas_ffd, qttd_ffd = aplicar_ffd(comprimento_barra, comprimentos_itens, demandas_residuais.copy())
                
                print("\n-Solução inteira pela Heurística Construtiva FFD:")
               
                total_barras_ffd = 0
                soma_total_ffd=0
                soma_qttd=0

                tabela_ffd = []
                for padrao, perda, qttd in zip(padroes_ffd, perdas_ffd, qttd_ffd):
                    tabela_ffd.append([qttd] + padrao + [perda])
                    soma_total_ffd += perda
                    soma_qttd +=qttd
                    total_barras_ffd += sum(padrao)

                cabecalho_ffd = ["Quantidade"] + [f"Item {i+1}" for i in range(len(comprimentos_itens))] + ["Perda"]

                print(tabulate(tabela_ffd, headers=cabecalho_ffd, tablefmt="grid"))
                print(f"\n-Quantidade Total: {soma_qttd}")
                print(f"-Perda Total: {soma_total_ffd}")
                print(f"-Quantidade Total de Barras Utilizadas: {total_barras_ffd}")

        else: 
            resolver_problema_mestre_restrito_novo(melhores_padroes, melhores_perdas, demandas_residuais, comprimentos_itens, comprimento_barra)
    return modelo, melhores_padroes, melhores_perdas

def truncar_solucao(modelo, melhores_padroes, demandas):
    solucao_continua_y = [var.X for var in modelo.getVars()]
    solucao_truncada_y = [int(solucao_continua_y[i]) for i in range(len(solucao_continua_y)) if solucao_continua_y[i] > 0]
    demandas_residuais = demandas.copy()
    padroes_truncados = [melhores_padroes[i] for i in range(len(solucao_continua_y)) if solucao_continua_y[i] > 0]
    
    for i, y_truncado in enumerate(solucao_truncada_y):
        for j in range(len(demandas_residuais)):
            demandas_residuais[j] -= y_truncado * padroes_truncados[i][j]

    return solucao_truncada_y, demandas_residuais

def aplicar_ffd(comprimento_barra, comprimentos_itens, demandas_residuais):
    itens_ordenados = sorted(range(len(comprimentos_itens)), key=lambda i: comprimentos_itens[i], reverse=True)
    padroes_ffd = []
    perdas_ffd = []
    qttd_ffd = []
    while any(d> 0 for d in demandas_residuais):
        padrao_atual = [0] * len(comprimentos_itens)
        comprimento_usado = 0
        for i in itens_ordenados:
            while demandas_residuais[i] > 0 and (comprimento_usado + comprimentos_itens[i] <= comprimento_barra):
                padrao_atual[i] += 1
                demandas_residuais[i] -= 1
                comprimento_usado += comprimentos_itens[i]
        perda_atual = comprimento_barra - comprimento_usado
        padroes_ffd.append(padrao_atual)
        perdas_ffd.append(perda_atual)
        qttd_ffd.append(1)
    return padroes_ffd, perdas_ffd, qttd_ffd

def algoritmo_unidimensional_pmr():
    while True:
        resultado = algoritmo_unidimensional()
        if resultado == 'cancelar':
            print("Operação cancelada pelo usuário.")
            return None, None
        comprimento_barra, demandas, comprimentos_itens, padroes_filtrados, perdas_filtradas = resultado
        tabela_padroes, cabecalho = gerar_tabela_padroes(padroes_filtrados, perdas_filtradas)
        print("\n-Tabela de Padrões de Corte e Perdas:")
        print(tabulate(tabela_padroes, headers=cabecalho, tablefmt="grid"))
        funcao_objetivo, restricoes = funcao_objetivo_e_restricoes(padroes_filtrados, perdas_filtradas, demandas)
        print("\n-Função Objetivo:")
        print(funcao_objetivo)
        print("\n-Restrições:")
        for restricao in restricoes:
            print(restricao)
        melhores_padroes, melhores_perdas = preparar_padroes(padroes_filtrados, comprimento_barra, comprimentos_itens)
        custo_relativo = -1 

        while custo_relativo < 0:
            modelo = resolver_problema_mestre_restrito(melhores_padroes, melhores_perdas, demandas)
            if modelo:
                dual_values = obter_valores_duais(modelo, demandas)
                subproblema_modelo = resolver_subproblema_maximizacao(comprimento_barra, comprimentos_itens, dual_values)
                if subproblema_modelo:
                    custo_relativo = verificar_custo_relativo(subproblema_modelo)
                    if custo_relativo < 0:
                        nova_coluna = [int(var.X) for var in subproblema_modelo.getVars()]
                        melhores_padroes.append(nova_coluna)
                        comprimento_ocupado = sum(nova_coluna[i] * comprimentos_itens[i] for i in range(len(comprimentos_itens)))
                        nova_perda = comprimento_barra - comprimento_ocupado
                        melhores_perdas.append(nova_perda)
                else:
                    print("Falha ao resolver o subproblema de maximização.")
                    break
            else:
                print("Falha ao resolver o problema mestre restrito.")
                break
        padroes_utilizados = associar_padroes_solucao_otima(modelo, melhores_padroes)
        imprimir_tabela_solucao_otima(padroes_utilizados, comprimentos_itens,comprimento_barra)
        if custo_relativo >= 0:
            solucao_truncada_y, demandas_residuais = truncar_solucao(modelo, melhores_padroes, demandas)
            if all(y < 1 for y in solucao_truncada_y):
                padroes_ffd, perdas_ffd, qttd_ffd = aplicar_ffd(comprimento_barra, comprimentos_itens, demandas_residuais.copy())
                print("\n-Solução inteira pela Heurística Construtiva FFD:")
                total_barras_ffd = 0
                soma_total_ffd=0
                soma_qttd=0
                tabela_ffd = []
                for padrao, perda, qttd in zip(padroes_ffd, perdas_ffd, qttd_ffd):
                    tabela_ffd.append([qttd] + padrao + [perda])
                    soma_total_ffd += perda
                    soma_qttd +=qttd
                    total_barras_ffd += sum(padrao)
                cabecalho_ffd = ["Quantidade"] + [f"Item {i+1}" for i in range(len(comprimentos_itens))] + ["Perda"]

                print(tabulate(tabela_ffd, headers=cabecalho_ffd, tablefmt="grid"))
                print(f"\n-Quantidade Total: {soma_qttd}")
                print(f"-Perda Total: {soma_total_ffd}")
                print(f"-Quantidade Total de Barras Utilizadas: {total_barras_ffd}")

                
            else: 
                print("\n--> Aplicar Heurística para encontrar solução inteira.")
                imprimir_tabela_solucao_truncada(solucao_truncada_y, melhores_padroes, comprimentos_itens, comprimento_barra)
                if not all(d <= 0 for d in demandas_residuais):
                    resolver_problema_mestre_restrito_novo(melhores_padroes, melhores_perdas, demandas_residuais, comprimentos_itens, comprimento_barra)
    
                return
        
def imprimir_tabela_solucao_otima(padroes_utilizados, comprimentos_itens, comprimento_barra):
    tabela_resultado = []
    total_barras_utilizadas = 0
    soma_perda = 0

    headers = ["Quantidade Utilizada"] + [f"Item {i+1}" for i in range(len(comprimentos_itens))] + ["Perda"]

    for padrao, quantidade in padroes_utilizados:
        soma_itens_cortados = sum(padrao[i] * comprimentos_itens[i] for i in range(len(comprimentos_itens)))
        perda = comprimento_barra - soma_itens_cortados
        linha = [quantidade] + [padrao[i] for i in range(len(comprimentos_itens))] + [perda]
        tabela_resultado.append(linha)
        total_barras_utilizadas += sum(padrao)
        soma_perda += perda

    print("\n-Tabela da Solução Ótima:")
    print(tabulate(tabela_resultado, headers=headers, tablefmt="grid"))
    total_barras = sum(quantidade for _, quantidade in padroes_utilizados)
    print(f"\n-Quantidade Total: {total_barras}")
    print(f"-Perda Total: {soma_perda}")
    print(f"-Quantidade Total de Barras Utilizadas: {total_barras_utilizadas}")

def imprimir_tabela_solucao_truncada(solucao_truncada, melhores_padroes, comprimentos_itens, comprimento_barra):
    tabela_truncada = []
    total_barras_utilizadas = 0
    soma_perda=0
    soma_qttd=0

    melhores_padroes_filtrados = [list(padrao) for padrao in melhores_padroes if isinstance(padrao, list)]
    indice_padroes = 0
    
    for y_truncado in solucao_truncada:
        if y_truncado > 0 and indice_padroes < len(melhores_padroes_filtrados):

            soma_itens_cortados = sum(melhores_padroes_filtrados[indice_padroes][i] * comprimentos_itens[i] for i in range(len(comprimentos_itens)))
            perda = comprimento_barra - soma_itens_cortados
            linha = [y_truncado] + list(melhores_padroes_filtrados[indice_padroes]) + [perda]
            tabela_truncada.append(linha)
            soma_perda += perda
            soma_qttd += y_truncado
            total_barras_utilizadas += sum(melhores_padroes_filtrados[indice_padroes])
        
        if y_truncado > 0:
            indice_padroes += 1
    
    headers_truncada = ["Quantidade"] + [f"Item {i+1}" for i in range(len(comprimentos_itens))] + ["Perda"]
    print("\n-Tabela da Solução pela Heurística residual com Truncamento:")
    print(tabulate(tabela_truncada, headers=headers_truncada, tablefmt="grid"))
    print(f"\n-Quantidade Total: {soma_qttd}")
    print(f"-Perda Total: {soma_perda}")
    print(f"-Quantidade Total de Barras Utilizadas: {total_barras_utilizadas}")

def associar_padroes_solucao_otima(modelo, melhores_padroes):
    solucao_y = [var.X for var in modelo.getVars()]
    padroes_utilizados = [(melhores_padroes[i], solucao_y[i]) for i in range(len(solucao_y)) if solucao_y[i] > 0]
    return padroes_utilizados

def preparar_padroes(padroes_filtrados, comprimento_barra, comprimentos_itens):
    padroes_homogeneos = filtrar_padroes_homogeneos(padroes_filtrados)
    return selecionar_melhor_padrao_homogeneo(padroes_homogeneos, comprimento_barra, comprimentos_itens)

def obter_valores_duais(modelo, demandas):
    return [modelo.getConstrs()[j].Pi for j in range(len(demandas))]

def verificar_custo_relativo(subproblema_modelo):
    solucao_otima_subproblema = subproblema_modelo.objVal
    custo_relativo = 1 - solucao_otima_subproblema
    return custo_relativo

algoritmo_unidimensional_pmr()