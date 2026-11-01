"""Solo conteggi/categorie/byte: nessun valore finanziario nelle metriche."""
import json

AMOUNTS={'remaining_principal','payment_amount','annual_interest'}


def view_metrics(view,prefix):
    data=view.model_dump(mode='json') if hasattr(view,'model_dump') else view
    full='financial_profile' in data
    fields={k for k,v in data['financial_profile'].items() if v is not None} if full else set(data)
    return {prefix+'_bytes':len(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()),
            prefix+'_fields':len(fields),prefix+'_exact_amount_fields':len(fields&AMOUNTS) if full else 0,
            prefix+'_exact_date_fields':len(fields) if full else 0,
            prefix+'_exact_duration_fields':int(full and 'remaining_months' in fields)}
