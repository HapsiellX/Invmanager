"""
Debug helper for notification system issues
"""

import streamlit as st
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from database.models.cable import Cable
from database.models.hardware import HardwareItem
from database.models.location import Location
from database.models.audit_log import AuditLog


def debug_notification_data_types(db: Session) -> Dict[str, Any]:
    """Debug data types returned by database queries"""
    results = {
        'cable_test': None,
        'hardware_test': None,
        'location_test': None,
        'audit_test': None,
        'errors': []
    }

    # Test Cable query
    try:
        cable = db.query(Cable).first()
        if cable:
            results['cable_test'] = {
                'object_type': str(type(cable)),
                'has_id_attr': hasattr(cable, 'id'),
                'has_id_key': hasattr(cable, '__getitem__') and 'id' in cable.__dict__ if hasattr(cable, '__dict__') else False,
                'id_value': getattr(cable, 'id', None),
                'id_via_dict': cable.__dict__.get('id') if hasattr(cable, '__dict__') else None,
                'all_attributes': list(cable.__dict__.keys()) if hasattr(cable, '__dict__') else [],
                'is_dict': isinstance(cable, dict),
                'to_dict_available': hasattr(cable, 'to_dict')
            }

            # Test standort relationship
            if hasattr(cable, 'standort'):
                standort = cable.standort
                if standort:
                    results['cable_test']['standort_type'] = str(type(standort))
                    results['cable_test']['standort_has_name'] = hasattr(standort, 'name')
                    results['cable_test']['standort_name'] = getattr(standort, 'name', None)

    except Exception as e:
        results['errors'].append(f"Cable test failed: {e}")

    # Test Hardware query
    try:
        hardware = db.query(HardwareItem).first()
        if hardware:
            results['hardware_test'] = {
                'object_type': str(type(hardware)),
                'has_id_attr': hasattr(hardware, 'id'),
                'id_value': getattr(hardware, 'id', None),
                'is_dict': isinstance(hardware, dict),
                'to_dict_available': hasattr(hardware, 'to_dict')
            }
    except Exception as e:
        results['errors'].append(f"Hardware test failed: {e}")

    # Test Location query
    try:
        location = db.query(Location).first()
        if location:
            results['location_test'] = {
                'object_type': str(type(location)),
                'has_id_attr': hasattr(location, 'id'),
                'id_value': getattr(location, 'id', None),
                'is_dict': isinstance(location, dict),
                'to_dict_available': hasattr(location, 'to_dict')
            }
    except Exception as e:
        results['errors'].append(f"Location test failed: {e}")

    # Test AuditLog query
    try:
        audit = db.query(AuditLog).first()
        if audit:
            results['audit_test'] = {
                'object_type': str(type(audit)),
                'has_id_attr': hasattr(audit, 'id'),
                'id_value': getattr(audit, 'id', None),
                'is_dict': isinstance(audit, dict),
                'to_dict_available': hasattr(audit, 'to_dict')
            }
    except Exception as e:
        results['errors'].append(f"Audit test failed: {e}")

    return results


def show_notification_debug_panel(db: Session):
    """Show notification debug panel in Streamlit"""
    st.subheader("🔍 Notification System Debug")

    if st.button("🧪 Run Database Type Analysis", key="run_db_type_analysis"):
        with st.spinner("Analyzing database query results..."):
            results = debug_notification_data_types(db)

            st.subheader("📊 Analysis Results")

            # Show errors first
            if results['errors']:
                st.error("❌ Errors encountered:")
                for error in results['errors']:
                    st.text(f"  - {error}")

            # Show Cable analysis
            if results['cable_test']:
                with st.expander("🔌 Cable Query Analysis"):
                    cable_data = results['cable_test']

                    col1, col2 = st.columns(2)
                    with col1:
                        st.text(f"Object Type: {cable_data['object_type']}")
                        st.text(f"Has .id attribute: {cable_data['has_id_attr']}")
                        st.text(f"Is Dictionary: {cable_data['is_dict']}")
                        st.text(f"Has to_dict(): {cable_data['to_dict_available']}")

                    with col2:
                        st.text(f"ID Value: {cable_data['id_value']}")
                        st.text(f"ID via dict: {cable_data['id_via_dict']}")

                    if cable_data['all_attributes']:
                        st.text("Available attributes:")
                        st.text(", ".join(cable_data['all_attributes'][:10]))

                    # Standort relationship analysis
                    if 'standort_type' in cable_data:
                        st.text(f"Standort Type: {cable_data['standort_type']}")
                        st.text(f"Standort has name: {cable_data['standort_has_name']}")
                        st.text(f"Standort name: {cable_data['standort_name']}")

            # Show other analyses
            for test_name, test_key in [('Hardware', 'hardware_test'), ('Location', 'location_test'), ('Audit', 'audit_test')]:
                if results[test_key]:
                    with st.expander(f"📋 {test_name} Query Analysis"):
                        test_data = results[test_key]
                        for key, value in test_data.items():
                            st.text(f"{key}: {value}")

    # Test safe accessor function
    if st.button("🛡️ Test Safe Accessor Function", key="test_safe_accessor"):
        with st.spinner("Testing safe accessor..."):
            try:
                from .services import NotificationService

                # Create notification service
                ns = NotificationService(db)

                # Test with actual cable object
                cable = db.query(Cable).first()
                if cable:
                    st.success("✅ Safe accessor test with Cable:")

                    # Test different access methods
                    direct_id = ns._safe_get_attr(cable, 'id', 'FAILED')
                    direct_typ = ns._safe_get_attr(cable, 'typ', 'FAILED')
                    nonexistent = ns._safe_get_attr(cable, 'nonexistent_attr', 'DEFAULT')

                    st.text(f"cable.id via safe accessor: {direct_id}")
                    st.text(f"cable.typ via safe accessor: {direct_typ}")
                    st.text(f"nonexistent attribute: {nonexistent}")

                    # Test with converted dictionary
                    if hasattr(cable, 'to_dict'):
                        cable_dict = cable.to_dict()
                        dict_id = ns._safe_get_attr(cable_dict, 'id', 'FAILED')
                        st.text(f"cable_dict['id'] via safe accessor: {dict_id}")

            except Exception as e:
                st.error(f"❌ Safe accessor test failed: {e}")
                import traceback
                st.code(traceback.format_exc())


def test_notification_methods(db: Session):
    """Test individual notification methods"""
    st.subheader("🧪 Notification Methods Test")

    try:
        from .services import NotificationService
        ns = NotificationService(db)

        methods_to_test = [
            ('_get_stock_alerts', '📦 Stock Alerts'),
            ('_get_warranty_alerts', '⏰ Warranty Alerts'),
            ('_get_critical_action_alerts', '🚨 Critical Action Alerts'),
            ('_get_system_alerts', '⚙️ System Alerts')
        ]

        for method_name, display_name in methods_to_test:
            if st.button(f"Test {display_name}", key=f"test_{method_name}"):
                with st.spinner(f"Testing {display_name}..."):
                    try:
                        method = getattr(ns, method_name)
                        alerts = method()

                        st.success(f"✅ {display_name}: {len(alerts)} alerts generated")

                        if alerts:
                            with st.expander(f"Sample {display_name}"):
                                st.json(alerts[0])

                    except Exception as e:
                        st.error(f"❌ {display_name} failed: {e}")
                        import traceback
                        st.code(traceback.format_exc())

    except Exception as e:
        st.error(f"❌ Could not create NotificationService: {e}")
        import traceback
        st.code(traceback.format_exc())