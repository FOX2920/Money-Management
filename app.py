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

# Lấy URL từ environment variable hoặc input của user
def get_sheet_url():
    # Thử lấy từ environment variable trước
    sheet_url = os.getenv('SHEET_URL_KEY')
    
    if not sheet_url:
        # Nếu không có, yêu cầu user nhập
        st.sidebar.header("🔧 Cấu hình")
        sheet_url = st.sidebar.text_input(
            "Google Apps Script URL:",
            help="Nhập URL Google Apps Script đã deploy",
            type="password"
        )
        
        if sheet_url:
            # Lưu vào session state để không phải nhập lại
            st.session_state.sheet_url = sheet_url
        elif 'sheet_url' in st.session_state:
            sheet_url = st.session_state.sheet_url
            
    return sheet_url

SHEET_URL_KEY = get_sheet_url()

if not SHEET_URL_KEY:
    st.error("❌ Vui lòng cung cấp Google Apps Script URL")
    st.info("💡 **Hướng dẫn thiết lập:**")
    st.markdown("""
    ### Cách lấy Google Apps Script URL:
    1. Truy cập [Google Apps Script](https://script.google.com)
    2. Tạo project mới và paste code Google Apps Script
    3. Deploy as Web App với settings:
       - Execute as: **Me** 
       - Who has access: **Anyone**
    4. Copy URL và paste vào ô bên trái
    """)
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

def test_connection():
    """Test kết nối với Google Apps Script"""
    try:
        data = {"action": "test_connection"}
        response = requests.post(
            SHEET_URL_KEY, 
            json=data, 
            timeout=30,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'StreamlitApp/1.0'
            }
        )
        
        if response.status_code == 200:
            return True, "✅ Kết nối thành công!"
        else:
            return False, f"❌ Lỗi kết nối: {response.status_code} - {response.text[:200]}"
            
    except Exception as e:
        return False, f"❌ Lỗi kết nối: {str(e)}"

def send_to_sheet(data):
    """Gửi dữ liệu đến Google Apps Script với xử lý lỗi cải tiến"""
    try:
        with st.spinner('Đang gửi dữ liệu...'):
            # Thêm retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        SHEET_URL_KEY, 
                        json=data, 
                        timeout=60,
                        headers={
                            'Content-Type': 'application/json',
                            'User-Agent': 'StreamlitApp/1.0',
                            'Accept': 'application/json'
                        }
                    )
                    
                    # Detailed error handling
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            if response_data.get('error'):
                                return False, f"❌ Lỗi từ server: {response_data.get('message', 'Unknown error')}"
                            
                            # Reset cache khi có cập nhật
                            st.session_state.last_update = time.time()
                            st.session_state.cached_summary = None
                            return True, "✅ Dữ liệu đã được cập nhật thành công!"
                        except json.JSONDecodeError:
                            return False, f"❌ Phản hồi không hợp lệ từ server"
                            
                    elif response.status_code == 401:
                        return False, """
❌ **Lỗi 401 - Unauthorized**

**Nguyên nhân có thể:**
1. Google Apps Script chưa được deploy đúng cách
2. Cấu hình quyền truy cập chưa đúng

**Cách khắc phục:**
1. Vào Google Apps Script → Deploy → New deployment
2. Type: Web app
3. Execute as: **Me**
4. Who has access: **Anyone** 
5. Deploy và copy URL mới
                        """
                    elif response.status_code == 403:
                        return False, "🔒 Không có quyền truy cập. Kiểm tra cấu hình Google Apps Script"
                    elif response.status_code == 404:
                        return False, "❌ URL không tồn tại. Kiểm tra lại Google Apps Script URL"
                    elif response.status_code == 429:
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        return False, "⏰ Quá nhiều yêu cầu, vui lòng thử lại sau"
                    else:
                        return False, f"❌ Lỗi {response.status_code}: {response.text[:200]}"
                        
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return False, "⏰ Kết nối quá chậm, vui lòng thử lại"
                except requests.exceptions.ConnectionError:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return False, "❌ Lỗi kết nối mạng"
                    
        return False, "❌ Không thể kết nối sau nhiều lần thử"
        
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
                timeout=45,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'StreamlitApp/1.0'
                }
            )
            
            if response.status_code == 200:
                try:
                    summary_data = response.json()
                    if summary_data.get('error'):
                        return False, f"Lỗi: {summary_data.get('message', 'Unknown error')}"
                    
                    # Cache kết quả
                    st.session_state.cached_summary = summary_data
                    st.session_state.last_update = time.time()
                    return True, summary_data
                except json.JSONDecodeError:
                    return False, "Phản hồi không hợp lệ từ server"
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
    
    # Test connection button in sidebar
    with st.sidebar:
        st.header("🔧 Kiểm tra kết nối")
        if st.button("🔍 Test kết nối", type="secondary"):
            success, message = test_connection()
            if success:
                st.success(message)
            else:
                st.error(message)
        
        st.markdown("---")
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
        ### 🔧 Thiết lập ban đầu:
        1. **Tạo Google Apps Script:**
           - Truy cập [script.google.com](https://script.google.com)
           - Tạo project mới và copy code Google Apps Script
           
        2. **Deploy Web App:**
           - Trong Apps Script: Deploy → New deployment
           - Type: **Web app**
           - Execute as: **Me**
           - Who has access: **Anyone**
           - Copy URL và paste vào app
           
        3. **Cấp quyền:**
           - Lần đầu deploy sẽ yêu cầu cấp quyền
           - Chấp nhận tất cả permissions
        
        ### 📱 Sử dụng hàng ngày:
        1. **Chọn thời gian:** Sử dụng sidebar để chọn tháng/năm
        2. **Thêm giao dịch:** Sử dụng form trong các tab
        3. **Xem báo cáo:** Tab báo cáo tự động cập nhật
        4. **Test kết nối:** Dùng nút test nếu gặp lỗi
        
        ### ⚠️ Xử lý lỗi thường gặp:
        - **Lỗi 401:** Deploy lại Google Apps Script với đúng cấu hình
        - **Lỗi 403:** Kiểm tra quyền truy cập
        - **Timeout:** Thử lại hoặc kiểm tra kết nối mạng
        """)

if __name__ == "__main__":
    main()
