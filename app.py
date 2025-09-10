import streamlit as st
import requests
import json
import os
from datetime import datetime, date, timedelta
import pandas as pd
import time

# Cấu hình trang
st.set_page_config(
    page_title="Quản lý Thu Chi Cá Nhân",
    page_icon="💰",
    layout="wide"
)

# Khởi tạo session state
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'cached_summary' not in st.session_state:
    st.session_state.cached_summary = None

# Lấy URL từ environment variable
SHEET_URL_KEY = os.getenv('SHEET_URL_KEY')

if not SHEET_URL_KEY:
    st.error("❌ Vui lòng thiết lập biến môi trường SHEET_URL_KEY")
    st.info("💡 **Hướng dẫn thiết lập:**")
    st.code("export SHEET_URL_KEY='your_google_apps_script_url'")
    st.stop()

# Danh mục thu chi
INCOME_CATEGORIES = ["Lương", "Thưởng", "Kinh doanh", "Đầu tư", "Khác"]
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
    "Mua sắm",
    "Giải trí",
    "Học tập",
    "Khác"
]

def validate_amount(amount):
    """Kiểm tra tính hợp lệ của số tiền"""
    if amount <= 0:
        return False, "Số tiền phải lớn hơn 0"
    if amount > 1000000000:  # 1 tỷ
        return False, "Số tiền quá lớn (tối đa 1 tỷ VNĐ)"
    return True, ""

def validate_date(input_date):
    """Kiểm tra tính hợp lệ của ngày"""
    today = date.today()
    if input_date > today:
        return False, "Không thể chọn ngày trong tương lai"
    if input_date < date(2020, 1, 1):
        return False, "Ngày không hợp lệ (từ năm 2020 trở lên)"
    return True, ""

def send_to_sheet(data):
    """Gửi dữ liệu đến Google Apps Script với xử lý lỗi cải tiến"""
    try:
        # Kiểm tra kết nối internet cơ bản
        test_response = requests.get("https://www.google.com", timeout=5)
        if test_response.status_code != 200:
            return False, "❌ Không có kết nối internet"
            
    except requests.exceptions.RequestException:
        return False, "❌ Không có kết nối internet"
    
    try:
        with st.spinner('Đang gửi dữ liệu...'):
            response = requests.post(
                SHEET_URL_KEY, 
                json=data, 
                timeout=45,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                # Reset cache khi có cập nhật
                st.session_state.last_update = time.time()
                st.session_state.cached_summary = None
                return True, "✅ Dữ liệu đã được cập nhật thành công!"
            elif response.status_code == 429:
                return False, "⏰ Quá nhiều yêu cầu, vui lòng thử lại sau"
            elif response.status_code == 403:
                return False, "🔒 Không có quyền truy cập, kiểm tra URL"
            else:
                return False, f"❌ Lỗi máy chủ: {response.status_code}"
                
    except requests.exceptions.Timeout:
        return False, "⏰ Kết nối quá chậm, vui lòng thử lại"
    except requests.exceptions.ConnectionError:
        return False, "❌ Lỗi kết nối đến máy chủ"
    except Exception as e:
        return False, f"❌ Lỗi không xác định: {str(e)[:100]}"

def get_summary_data(sheet_name):
    """Lấy dữ liệu báo cáo với cache"""
    # Kiểm tra cache (cache trong 5 phút)
    if (st.session_state.cached_summary and 
        st.session_state.last_update and 
        time.time() - st.session_state.last_update < 300):
        return True, st.session_state.cached_summary
    
    data = {
        "action": "get_summary",
        "sheet_name": sheet_name
    }
    
    try:
        with st.spinner('Đang tải báo cáo...'):
            response = requests.post(
                SHEET_URL_KEY, 
                json=data, 
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                summary_data = response.json()
                # Cache kết quả
                st.session_state.cached_summary = summary_data
                st.session_state.last_update = time.time()
                return True, summary_data
            else:
                return False, f"Lỗi {response.status_code}: Không thể tải báo cáo"
                
    except requests.exceptions.Timeout:
        return False, "Timeout: Không thể tải báo cáo"
    except Exception as e:
        return False, f"Lỗi: {str(e)[:100]}"

def format_currency(amount):
    """Format số tiền theo định dạng VN"""
    try:
        return f"{int(amount):,}".replace(',', '.') + " VNĐ"
    except:
        return "0 VNĐ"

def main():
    st.title("💰 Quản Lý Thu Chi Cá Nhân")
    
    # Sidebar để chọn tháng/năm
    with st.sidebar:
        st.header("📅 Chọn thời gian")
        
        # Sử dụng date input để chọn tháng/năm dễ dàng hơn
        today = datetime.now()
        selected_date = st.date_input(
            "Chọn tháng/năm:",
            value=today.date(),
            min_value=date(2020, 1, 1),
            max_value=today.date(),
            help="Chọn một ngày bất kỳ trong tháng bạn muốn quản lý"
        )
        
        selected_month = selected_date.month
        selected_year = selected_date.year
        
        sheet_name = f"{selected_month:02d}/{selected_year}"
        st.info(f"📊 Sheet hiện tại: **{sheet_name}**")
        
        # Thêm nút clear cache
        if st.button("🔄 Làm mới dữ liệu"):
            st.session_state.cached_summary = None
            st.session_state.last_update = None
            st.rerun()

    # Tabs chính
    tab1, tab2, tab3 = st.tabs(["💵 Thu Nhập", "💸 Chi Tiêu", "📊 Báo Cáo"])
    
    # Tab Thu Nhập
    with tab1:
        st.header("💵 Ghi Nhận Thu Nhập")
        
        with st.form("income_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                income_date = st.date_input(
                    "📅 Ngày:", 
                    value=today.date(),
                    max_value=today.date(),
                    min_value=date(selected_year, selected_month, 1),
                    help="Chọn ngày thu nhập"
                )
                income_category = st.selectbox(
                    "📂 Danh mục:", 
                    INCOME_CATEGORIES,
                    help="Chọn loại thu nhập"
                )
            
            with col2:
                income_amount = st.number_input(
                    "💰 Số tiền (VNĐ):", 
                    min_value=0,
                    max_value=1000000000,
                    step=1000,
                    help="Nhập số tiền thu nhập"
                )
                income_note = st.text_input(
                    "📝 Ghi chú:", 
                    max_chars=200,
                    help="Mô tả chi tiết (tùy chọn)"
                )
            
            submitted = st.form_submit_button("✅ Thêm Thu Nhập", type="primary")
            
            if submitted:
                # Validate dữ liệu
                amount_valid, amount_msg = validate_amount(income_amount)
                date_valid, date_msg = validate_date(income_date)
                
                if not amount_valid:
                    st.error(f"❌ {amount_msg}")
                elif not date_valid:
                    st.error(f"❌ {date_msg}")
                else:
                    data = {
                        "action": "add_transaction",
                        "sheet_name": sheet_name,
                        "transaction": {
                            "date": income_date.strftime("%Y-%m-%d"),
                            "type": "Thu",
                            "category": income_category,
                            "amount": income_amount,
                            "note": income_note.strip()
                        }
                    }
                    
                    success, message = send_to_sheet(data)
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)

    # Tab Chi Tiêu
    with tab2:
        st.header("💸 Ghi Nhận Chi Tiêu")
        
        with st.form("expense_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                expense_date = st.date_input(
                    "📅 Ngày:", 
                    value=today.date(),
                    max_value=today.date(),
                    min_value=date(selected_year, selected_month, 1),
                    help="Chọn ngày chi tiêu"
                )
                expense_category = st.selectbox(
                    "📂 Danh mục:", 
                    EXPENSE_CATEGORIES,
                    help="Chọn loại chi tiêu"
                )
            
            with col2:
                expense_amount = st.number_input(
                    "💰 Số tiền (VNĐ):", 
                    min_value=0,
                    max_value=1000000000,
                    step=1000,
                    help="Nhập số tiền chi tiêu"
                )
                expense_note = st.text_input(
                    "📝 Ghi chú:", 
                    max_chars=200,
                    help="Mô tả chi tiết (tùy chọn)"
                )
            
            submitted = st.form_submit_button("✅ Thêm Chi Tiêu", type="primary")
            
            if submitted:
                # Validate dữ liệu
                amount_valid, amount_msg = validate_amount(expense_amount)
                date_valid, date_msg = validate_date(expense_date)
                
                if not amount_valid:
                    st.error(f"❌ {amount_msg}")
                elif not date_valid:
                    st.error(f"❌ {date_msg}")
                else:
                    data = {
                        "action": "add_transaction",
                        "sheet_name": sheet_name,
                        "transaction": {
                            "date": expense_date.strftime("%Y-%m-%d"),
                            "type": "Chi",
                            "category": expense_category,
                            "amount": expense_amount,
                            "note": expense_note.strip()
                        }
                    }
                    
                    success, message = send_to_sheet(data)
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)

    # Tab Báo Cáo
    with tab3:
        st.header(f"📊 Báo Cáo Tháng {selected_month:02d}/{selected_year}")
        
        # Auto load báo cáo
        success, result = get_summary_data(sheet_name)
        
        if success:
            summary_data = result
            
            # Metrics chính
            col1, col2, col3 = st.columns(3)
            
            total_income = summary_data.get('total_income', 0)
            total_expense = summary_data.get('total_expense', 0)
            balance = total_income - total_expense
            
            with col1:
                st.metric(
                    "💵 Tổng Thu", 
                    format_currency(total_income)
                )
            
            with col2:
                st.metric(
                    "💸 Tổng Chi", 
                    format_currency(total_expense)
                )
            
            with col3:
                st.metric(
                    "💰 Số Dư", 
                    format_currency(balance),
                    delta=f"{balance:,.0f} VNĐ".replace(',', '.'),
                    delta_color="normal" if balance >= 0 else "inverse"
                )
            
            # Biểu đồ và bảng chi tiết
            if total_expense > 0 and 'expense_by_category' in summary_data:
                st.subheader("📈 Chi Tiết Chi Tiêu Theo Danh Mục")
                
                expense_data = summary_data['expense_by_category']
                if expense_data:
                    # Tạo DataFrame
                    df = pd.DataFrame(
                        list(expense_data.items()),
                        columns=['Danh Mục', 'Số Tiền']
                    )
                    df['Tỷ lệ %'] = (df['Số Tiền'] / total_expense * 100).round(1)
                    df['Số Tiền (VNĐ)'] = df['Số Tiền'].apply(format_currency)
                    
                    # Sắp xếp theo số tiền giảm dần
                    df = df.sort_values('Số Tiền', ascending=False)
                    
                    # Hiển thị bảng
                    st.dataframe(
                        df[['Danh Mục', 'Số Tiền (VNĐ)', 'Tỷ lệ %']], 
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Biểu đồ tròn
                    st.subheader("🥧 Biểu Đồ Phân Bổ Chi Tiêu")
                    chart_data = df.set_index('Danh Mục')['Số Tiền']
                    st.bar_chart(chart_data)
            
            # Thông tin bổ sung
            if st.session_state.last_update:
                update_time = datetime.fromtimestamp(st.session_state.last_update)
                st.caption(f"📅 Cập nhật lần cuối: {update_time.strftime('%H:%M:%S %d/%m/%Y')}")
        
        else:
            st.error(f"❌ {result}")
            if st.button("🔄 Thử lại"):
                st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("💡 **Hướng dẫn sử dụng:**")
    with st.expander("📖 Xem hướng dẫn chi tiết"):
        st.markdown("""
        1. **Thiết lập:** Đặt biến môi trường `SHEET_URL_KEY` với URL Google Apps Script
        2. **Chọn thời gian:** Sử dụng sidebar để chọn tháng/năm cần quản lý
        3. **Thêm giao dịch:** Sử dụng form trong các tab để thêm thu nhập và chi tiêu
        4. **Xem báo cáo:** Tab báo cáo sẽ tự động hiển thị thống kê tháng hiện tại
        5. **Làm mới:** Sử dụng nút "Làm mới dữ liệu" nếu cần cập nhật thông tin
        
        **Lưu ý:**
        - Số tiền tối đa: 1 tỷ VNĐ
        - Không thể chọn ngày trong tương lai
        - Dữ liệu được cache 5 phút để tăng tốc độ
        """)

if __name__ == "__main__":
    main()
