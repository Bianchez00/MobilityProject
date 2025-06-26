#%% 
# Verifica le colonne disponibili nei DataFrame
print("Colonne in Df_Calcolo_Settimanale:")
print(Df_Calcolo_Settimanale.columns.tolist())
print("\nColonne in Df_utenti:")
print(Df_utenti.columns.tolist())

# Verifica le prime righe per capire la struttura
print("\nPrime righe di Df_Calcolo_Settimanale:")
print(Df_Calcolo_Settimanale.head())
print("\nPrime righe di Df_utenti:")
print(Df_utenti.head())

#%%
# Soluzione alternativa: merge con nomi di colonna diversi
# Sostituisci 'nome_colonna_corretta' con il nome effettivo della colonna in Df_utenti
try:
    # Tenta il merge con il nome originale
    merged_df = pd.merge(Df_Calcolo_Settimanale, Df_utenti, on='user_id', how='inner')
    print("Merge completato con successo!")
except KeyError as e:
    print(f"Errore: {e}")
    print("Verifica i nomi delle colonne sopra e usa left_on e right_on per specificare nomi diversi")
    
    # Esempio di merge con nomi di colonna diversi:
    # merged_df = pd.merge(Df_Calcolo_Settimanale, Df_utenti, 
    #                     left_on='user_id', right_on='nome_colonna_corretta', how='inner')

# Se il merge ha successo, mostra il risultato
if 'merged_df' in locals():
    print(merged_df.head())