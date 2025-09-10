import streamlit as st
import requests
import json
import os
from datetime import datetime, date
import pandas as pd

# Cấu hình trang
st.set_page_config(
    page_title="Quản lý Thu Chi Cá Nhân",
    page_icon="💰",
    layout="wide"
)

# Lấy URL từ environment variable
SHEET_URL_KEY = os.getenv('SHEET_URL_KEY')

if not SHEET_URL_KEY:
    st.error("❌ Vui lòng thiết lập biến môi trường SHEET_URL_KEY")
    st.stop()

# Danh mục thu chi
INCOME_CATEGORIES = ["Lương"]
EXPENSE_CATEGORIES = [
    "Tiền ăn",
    "Tiền xăng di chuyển", 
    "Tiền trọ",
    "Tiền điện",
    "Tiền nước",
    "Tiền mạng 4G",
    "Sửa xe",
    "Y tế",
    "Dịch vụ mạng",
    "Khác"
]

def send_to_sheet(data):
    """Gửi dữ liệu đến Google Apps Script"""
    try:
        response = requests.post(SHEET_URL_KEY, json=data, timeout=30)
        if response.status_code == 200:
            return True, "Dữ liệu đã được cập nhật thành công!"
        else:
            return False, f"Lỗi: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Lỗi kết nối: {str(e)}"

def main():
    st.title("💰 Quản Lý Thu Chi Cá Nhân")
    
    # Sidebar để chọn tháng/năm
    with st.sidebar:
        st.header("📅 Chọn thời gian")
        selected_month = st.selectbox(
            "Tháng:",
            range(1, 13),
            index=datetime.now().month - 1,
            format_func=lambda x: f"Tháng {x}"
        )
        selected_year = st.selectbox(
            "Năm:",
            range(2020, 2030),
            index=datetime.now().year - 2020
        )
        
        sheet_name = f"{selected_month:02d}/{selected_year}"
        st.info(f"📊 Sheet hiện tại: **{sheet_name}**")

    # Tabs chính
    tab1, tab2, tab3 = st.tabs(["💵 Thu Nhập", "💸 Chi Tiêu", "📊 Báo Cáo"])
    
    # Tab Thu Nhập
    with tab1:
        st.header("💵 Ghi Nhận Thu Nhập")
        
        col1, col2 = st.columns(2)
        with col1:
            income_date = st.date_input("📅 Ngày:", key="income_date")
            income_category = st.selectbox("📂 Danh mục:", INCOME_CATEGORIES, key="income_category")
        
        with col2:
            income_amount = st.number_input("💰 Số tiền (VNĐ):", min_value=0, step=1000, key="income_amount")
            income_note = st.text_input("📝 Ghi chú:", key="income_note")
        
        if st.button("✅ Thêm Thu Nhập", type="primary"):
            if income_amount > 0:
                data = {
                    "action": "add_transaction",
                    "sheet_name": sheet_name,
                    "transaction": {
                        "date": income_date.strftime("%Y-%m-%d"),
                        "type": "Thu",
                        "category": income_category,
                        "amount": income_amount,
                        "note": income_note
                    }
                }
                
                success, message = send_to_sheet(data)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.error("❌ Vui lòng nhập số tiền hợp lệ!")

    # Tab Chi Tiêu
    with tab2:
        st.header("💸 Ghi Nhận Chi Tiêu")
        
        col1, col2 = st.columns(2)
        with col1:
            expense_date = st.date_input("📅 Ngày:", key="expense_date")
            expense_category = st.selectbox("📂 Danh mục:", EXPENSE_CATEGORIES, key="expense_category")
        
        with col2:
            expense_amount = st.number_input("💰 Số tiền (VNĐ):", min_value=0, step=1000, key="expense_amount")
            expense_note = st.text_input("📝 Ghi chú:", key="expense_note")
        
        if st.button("✅ Thêm Chi Tiêu", type="primary"):
            if expense_amount > 0:
                data = {
                    "action": "add_transaction",
                    "sheet_name": sheet_name,
                    "transaction": {
                        "date": expense_date.strftime("%Y-%m-%d"),
                        "type": "Chi",
                        "category": expense_category,
                        "amount": expense_amount,
                        "note": expense_note
                    }
                }
                
                success, message = send_to_sheet(data)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.error("❌ Vui lòng nhập số tiền hợp lệ!")

    # Tab Báo Cáo
    with tab3:
        st.header("📊 Báo Cáo Tháng " + sheet_name)
        
        col1, col2 = st.columns(2)
        
        if st.button("🔄 Lấy Báo Cáo", type="primary"):
            data = {
                "action": "get_summary",
                "sheet_name": sheet_name
            }
            
            try:
                response = requests.post(SHEET_URL_KEY, json=data, timeout=30)
                if response.status_code == 200:
                    summary_data = response.json()
                    
                    with col1:
                        st.metric("💵 Tổng Thu", f"{summary_data.get('total_income', 0):,} VNĐ")
                        st.metric("💸 Tổng Chi", f"{summary_data.get('total_expense', 0):,} VNĐ")
                    
                    with col2:
                        balance = summary_data.get('total_income', 0) - summary_data.get('total_expense', 0)
                        st.metric("💰 Số Dư", f"{balance:,} VNĐ", delta=balance)
                    
                    # Hiển thị chi tiết theo danh mục
                    if 'expense_by_category' in summary_data:
                        st.subheader("📈 Chi Tiết Chi Tiêu Theo Danh Mục")
                        
                        expense_df = pd.DataFrame(
                            list(summary_data['expense_by_category'].items()),
                            columns=['Danh Mục', 'Số Tiền']
                        )
                        expense_df['Số Tiền'] = expense_df['Số Tiền'].apply(lambda x: f"{x:,} VNĐ")
                        st.dataframe(expense_df, use_container_width=True)
                    
                else:
                    st.error("❌ Không thể lấy báo cáo!")
                    
            except Exception as e:
                st.error(f"❌ Lỗi kết nối: {str(e)}")

    # Footer
    st.markdown("---")
    st.markdown("💡 **Hướng dẫn sử dụng:**")
    st.markdown("1. Thiết lập biến môi trường `SHEET_URL_KEY` với URL Google Apps Script")
    st.markdown("2. Chọn tháng/năm ở sidebar")
    st.markdown("3. Thêm thu nhập và chi tiêu trong các tab tương ứng")
    st.markdown("4. Xem báo cáo trong tab 'Báo Cáo'")

if __name__ == "__main__":
    main()
