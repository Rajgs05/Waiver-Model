import json
import os

def validate_waiver_request(extracted_data):
    """
    Validates extracted waiver details against the SOA database with partial approval logic.
    Path: src/utils/validator.py
    """
    soa_db_path = "soa-data-server/soa_database"
    validated_results = []

    for detail in extracted_data.get("waiver_details", []):
        agreement_no = detail["Agreement Number"]
        extracted_waived_amt = float(detail["Total Amount to be Waived off"])
        
        soa_file_path = os.path.join(soa_db_path, f"{agreement_no}.json")
        
        recommendation = ""
        validation_status = "Pending"
        db_total_overdue = 0

        if os.path.exists(soa_file_path):
            with open(soa_file_path, 'r') as f:
                soa_data = json.load(f)
            
            summary_report = soa_data.get("statementOfAccount", {}).get("soa_summary_report", [])
            for component in summary_report:
                if component.get("component") == "total_overdue":
                    db_total_overdue = float(component.get("overdue", 0))
                    break
            
            # Logic Update:
            if extracted_waived_amt >= db_total_overdue:
                # Case 1: Full Overdue covered
                recommendation = "Waiver is approved"
                validation_status = "Passed"
            else:
                # Case 2: Partial Waiver (Extracted < DB Overdue)
                left_overdue = db_total_overdue - extracted_waived_amt
                recommendation = (f"Waiver is approved only for {extracted_waived_amt} amount "
                                  f"and the left overdue amount is {left_overdue}")
                validation_status = "Partial Approval"
        else:
            recommendation = f"Error: SOA file for {agreement_no} not found"
            validation_status = "Error"

        validated_results.append({
            **detail,
            "database_total_overdue": db_total_overdue,
            "validation_status": validation_status,
            "recommendation": recommendation
        })

    extracted_data["waiver_details"] = validated_results
    return extracted_data