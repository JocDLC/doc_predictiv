# Reparto equitativo de leads en Distribuir leads

## Problema

Cuando trabaja un equipo distinto al que tomó los leads (ej. sábado: Andres +
Jose Manuel; lunes festivo: solo Jose Manuel), los leads quedan a nombre de
quienes no trabajan. Hoy el módulo asigna destinos fijos desde el archivo;
falta repartir el lote **equitativamente entre quienes trabajan hoy** haciendo
la **menor cantidad de reasignaciones posible**, y generar la lista de leads
que pidieron WhatsApp con su nueva persona.

## Propuesta

Modo "Reparto equitativo" en la vista Distribuir leads:

- Parseo reutilizado: `lead_id`, auxiliar actual (columna del archivo) y flag
  WhatsApp (`Preferred mean of contact`).
- Equipo del día: lista persistente de auxiliares (alta/baja/tilde guardada);
  el usuario tilda quiénes trabajan.
- Algoritmo de reparto mínimo: cupo por persona (partes iguales, resto de a
  uno); los leads ya a nombre de alguien que trabaja se quedan hasta su cupo;
  el resto se mueve a quienes les falta.
- Vista previa existente con destino computado (marca "se queda"/"se mueve",
  editable) → misma cola → mismo runner real/simulación, sin cambios.
- Salidas: resultados por lead + lista "reasignación WhatsApp" (lead → nueva
  persona).

## Non-goals

- No cambia el runner ni los estados de resultado.
- No se reenvía WhatsApp: la lista solo informa destino nuevo.
- El reparto usa el auxiliar que declara el archivo (la simulación/real verifica
  el propietario real en Salesforce como siempre).
