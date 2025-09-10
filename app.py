import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import json
import requests
from io import BytesIO

# Cấu hình trang
st.set_page_config(
    page_title="Quản lý Thu Chi Cá nhân",
    page_icon="💰",
    layout="wide"
)

# CSS để làm đẹp giao diện
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .income-card {
        border-left-color: #2ca02c;
    }
    .expense-card {
        border-left-color: #d62728;
    }
    .balance-card {
        border-left-color: #ff7f0e;
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo session state
if 'transactions' not in st.session_state:
    st.session_state.transactions = []

if 'monthly_budget' not in st.session_state:
    st.session_state.monthly_budget = {
        'salary': 0,
        'food': 0,
        'transport': 0,
        'accommodation': 0,
        'utilities': 0,
        'miscellaneous': 0
    }

# Header
st.markdown('<h1 class="main-header">💰 Quản lý Thu Chi Cá nhân</h1>', unsafe_allow_html=True)

# Sidebar cho navigation
st.sidebar.title("📋 Menu")
page = st.sidebar.selectbox("Chọn chức năng", [
    "📊 Tổng quan", 
    "➕ Thêm giao dịch", 
    "📈 Báo cáo", 
    "⚙️ Cài đặt ngân sách",
    "📤 Xuất dữ liệu"
])

# Hàm thêm giao dịch
def add_transaction(date, category, subcategory, amount, description, type_):
    transaction = {
        'date': date.strftime('%Y-%m-%d'),
        'category': category,
        'subcategory': subcategory,
        'amount': amount,
        'description': description,
        'type': type_,
        'month': date.strftime('%Y-%m')
    }
    st.session_state.transactions.append(transaction)

# Hàm tính toán thống kê
def get_monthly_stats(month=None):
    df = pd.DataFrame(st.session_state.transactions)
    if df.empty:
        return 0, 0, 0
    
    if month:
        df = df[df['month'] == month]
    
    income = df[df['type'] == 'Thu'].groupby('month')['amount'].sum().sum() if not df.empty else 0
    expense = df[df['type'] == 'Chi'].groupby('month')['amount'].sum().sum() if not df.empty else 0
    balance = income - expense
    
    return income, expense, balance

# Hàm xuất dữ liệu cho Google Apps Script
def export_to_json():
    data = {
        'transactions': st.session_state.transactions,
        'budget': st.session_state.monthly_budget,
        'export_date': datetime.now().isoformat()
    }
    return json.dumps(data, ensure_ascii=False, indent=2)

# Trang Tổng quan
if page == "📊 Tổng quan":
    st.header("📊 Tổng quan tài chính")
    
    # Thống kê tháng hiện tại
    current_month = datetime.now().strftime('%Y-%m')
    income, expense, balance = get_monthly_stats(current_month)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card income-card">', unsafe_allow_html=True)
        st.metric("💰 Thu nhập tháng này", f"{income:,.0f} VNĐ")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card expense-card">', unsafe_allow_html=True)
        st.metric("💸 Chi tiêu tháng này", f"{expense:,.0f} VNĐ")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card balance-card">', unsafe_allow_html=True)
        st.metric("📊 Số dư", f"{balance:,.0f} VNĐ")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Biểu đồ tròn chi tiêu theo danh mục
    if st.session_state.transactions:
        df = pd.DataFrame(st.session_state.transactions)
        df_current = df[df['month'] == current_month]
        
        if not df_current.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Chi tiêu theo danh mục (tháng này)")
                expense_data = df_current[df_current['type'] == 'Chi']
                if not expense_data.empty:
                    expense_by_category = expense_data.groupby('category')['amount'].sum()
                    fig_pie = px.pie(
                        values=expense_by_category.values,
                        names=expense_by_category.index,
                        title="Phân bố chi tiêu"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.subheader("📈 Xu hướng thu chi")
                monthly_data = df.groupby(['month', 'type'])['amount'].sum().reset_index()
                if not monthly_data.empty:
                    fig_line = px.line(
                        monthly_data,
                        x='month',
                        y='amount',
                        color='type',
                        title="Xu hướng thu chi theo tháng"
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
    
    # Giao dịch gần đây
    st.subheader("🕒 Giao dịch gần đây")
    if st.session_state.transactions:
        recent_transactions = pd.DataFrame(st.session_state.transactions).tail(10)
        recent_transactions['amount_formatted'] = recent_transactions['amount'].apply(lambda x: f"{x:,.0f} VNĐ")
        st.dataframe(
            recent_transactions[['date', 'type', 'category', 'description', 'amount_formatted']].rename(columns={
                'date': 'Ngày',
                'type': 'Loại',
                'category': 'Danh mục',
                'description': 'Mô tả',
                'amount_formatted': 'Số tiền'
            }),
            use_container_width=True
        )
    else:
        st.info("Chưa có giao dịch nào được ghi nhận.")

# Trang Thêm giao dịch
elif page == "➕ Thêm giao dịch":
    st.header("➕ Thêm giao dịch mới")
    
    col1, col2 = st.columns(2)
    
    with col1:
        transaction_date = st.date_input("📅 Ngày giao dịch", value=date.today())
        transaction_type = st.selectbox("📊 Loại giao dịch", ["Thu", "Chi"])
        
        if transaction_type == "Thu":
            category = st.selectbox("💰 Danh mục thu", ["Lương", "Thưởng", "Thu nhập khác"])
            subcategory = st.text_input("📝 Danh mục con (tùy chọn)")
        else:
            category = st.selectbox("💸 Danh mục chi", [
                "Ăn uống", 
                "Di chuyển", 
                "Trọ/Nhà ở", 
                "Điện nước", 
                "Phí phát sinh",
                "Chi tiêu khác"
            ])
            
            subcategory_options = {
                "Ăn uống": ["Ăn sáng", "Ăn trưa", "Ăn tối", "Đồ uống", "Ăn vặt"],
                "Di chuyển": ["Xăng xe", "Xe bus", "Grab/Taxi", "Sửa xe"],
                "Trọ/Nhà ở": ["Tiền thuê", "Tiền cọc", "Chi phí khác"],
                "Điện nước": ["Tiền điện", "Tiền nước", "Internet", "Gas"],
                "Phí phát sinh": ["Y tế", "Mua sắm", "Giải trí", "Khác"],
                "Chi tiêu khác": ["Khác"]
            }
            
            subcategory = st.selectbox("📝 Danh mục con", subcategory_options.get(category, ["Khác"]))
    
    with col2:
        amount = st.number_input("💵 Số tiền (VNĐ)", min_value=0, step=1000)
        description = st.text_area("📝 Mô tả", placeholder="Nhập mô tả cho giao dịch...")
        
        if st.button("✅ Thêm giao dịch", type="primary"):
            if amount > 0:
                add_transaction(transaction_date, category, subcategory, amount, description, transaction_type)
                st.success(f"✅ Đã thêm giao dịch {transaction_type.lower()} {amount:,.0f} VNĐ!")
                st.rerun()
            else:
                st.error("❌ Vui lòng nhập số tiền hợp lệ!")

# Trang Báo cáo
elif page == "📈 Báo cáo":
    st.header("📈 Báo cáo chi tiết")
    
    if st.session_state.transactions:
        df = pd.DataFrame(st.session_state.transactions)
        
        # Bộ lọc
        col1, col2, col3 = st.columns(3)
        
        with col1:
            months = sorted(df['month'].unique(), reverse=True)
            selected_month = st.selectbox("📅 Chọn tháng", ["Tất cả"] + months)
        
        with col2:
            types = st.multiselect("📊 Loại giao dịch", ["Thu", "Chi"], default=["Thu", "Chi"])
        
        with col3:
            categories = st.multiselect("📝 Danh mục", df['category'].unique(), default=df['category'].unique())
        
        # Lọc dữ liệu
        filtered_df = df.copy()
        if selected_month != "Tất cả":
            filtered_df = filtered_df[filtered_df['month'] == selected_month]
        if types:
            filtered_df = filtered_df[filtered_df['type'].isin(types)]
        if categories:
            filtered_df = filtered_df[filtered_df['category'].isin(categories)]
        
        # Hiển thị báo cáo
        if not filtered_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Tổng kết")
                summary = filtered_df.groupby('type')['amount'].sum()
                for type_, amount in summary.items():
                    st.metric(f"{type} nhập" if type_ == "Thu" else f"{type} tiêu", f"{amount:,.0f} VNĐ")
            
            with col2:
                st.subheader("📈 Biểu đồ cột theo danh mục")
                category_data = filtered_df.groupby(['category', 'type'])['amount'].sum().reset_index()
                fig_bar = px.bar(
                    category_data,
                    x='category',
                    y='amount',
                    color='type',
                    title="Thu chi theo danh mục"
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Bảng chi tiết
            st.subheader("📋 Chi tiết giao dịch")
            filtered_df['amount_formatted'] = filtered_df['amount'].apply(lambda x: f"{x:,.0f} VNĐ")
            st.dataframe(
                filtered_df[['date', 'type', 'category', 'subcategory', 'description', 'amount_formatted']].rename(columns={
                    'date': 'Ngày',
                    'type': 'Loại',
                    'category': 'Danh mục',
                    'subcategory': 'Danh mục con',
                    'description': 'Mô tả',
                    'amount_formatted': 'Số tiền'
                }).sort_values('Ngày', ascending=False),
                use_container_width=True
            )
        else:
            st.info("Không có dữ liệu phù hợp với bộ lọc.")
    else:
        st.info("Chưa có dữ liệu để hiển thị báo cáo.")

# Trang Cài đặt ngân sách
elif page == "⚙️ Cài đặt ngân sách":
    st.header("⚙️ Cài đặt ngân sách hàng tháng")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Thu nhập")
        st.session_state.monthly_budget['salary'] = st.number_input(
            "Lương hàng tháng (VNĐ)", 
            value=st.session_state.monthly_budget['salary'],
            step=100000
        )
    
    with col2:
        st.subheader("💸 Ngân sách chi tiêu")
        st.session_state.monthly_budget['food'] = st.number_input(
            "Ăn uống (VNĐ)", 
            value=st.session_state.monthly_budget['food'],
            step=50000
        )
        st.session_state.monthly_budget['transport'] = st.number_input(
            "Di chuyển (VNĐ)", 
            value=st.session_state.monthly_budget['transport'],
            step=50000
        )
        st.session_state.monthly_budget['accommodation'] = st.number_input(
            "Trọ/Nhà ở (VNĐ)", 
            value=st.session_state.monthly_budget['accommodation'],
            step=100000
        )
        st.session_state.monthly_budget['utilities'] = st.number_input(
            "Điện nước (VNĐ)", 
            value=st.session_state.monthly_budget['utilities'],
            step=50000
        )
        st.session_state.monthly_budget['miscellaneous'] = st.number_input(
            "Phí phát sinh (VNĐ)", 
            value=st.session_state.monthly_budget['miscellaneous'],
            step=50000
        )
    
    total_budget = sum([v for k, v in st.session_state.monthly_budget.items() if k != 'salary'])
    st.metric("💰 Tổng ngân sách chi tiêu", f"{total_budget:,.0f} VNĐ")
    
    if st.session_state.monthly_budget['salary'] > 0:
        saving_rate = (st.session_state.monthly_budget['salary'] - total_budget) / st.session_state.monthly_budget['salary'] * 100
        st.metric("📈 Tỷ lệ tiết kiệm dự kiến", f"{saving_rate:.1f}%")

# Trang Xuất dữ liệu
elif page == "📤 Xuất dữ liệu":
    st.header("📤 Xuất dữ liệu")
    
    st.subheader("🔗 Tích hợp với Google Sheets")
    st.info("""
    Để tích hợp với Google Sheets:
    1. Tạo Google Apps Script với code bên dưới
    2. Deploy as Web App
    3. Nhập URL Web App vào ô bên dưới
    4. Nhấn 'Gửi dữ liệu' để cập nhật Google Sheets
    """)
    
    webapp_url = st.text_input("🔗 URL Google Apps Script Web App")
    
    if st.button("📤 Gửi dữ liệu lên Google Sheets"):
        if webapp_url and st.session_state.transactions:
            try:
                data = {
                    'transactions': st.session_state.transactions,
                    'budget': st.session_state.monthly_budget
                }
                response = requests.post(webapp_url, json=data)
                if response.status_code == 200:
                    st.success("✅ Đã gửi dữ liệu thành công!")
                else:
                    st.error(f"❌ Lỗi: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Lỗi kết nối: {str(e)}")
        elif not webapp_url:
            st.error("❌ Vui lòng nhập URL Web App!")
        else:
            st.error("❌ Không có dữ liệu để gửi!")
    
    st.subheader("💾 Xuất file")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📁 Tải xuống JSON"):
            if st.session_state.transactions:
                json_data = export_to_json()
                st.download_button(
                    label="💾 Tải file JSON",
                    data=json_data,
                    file_name=f"thu_chi_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
            else:
                st.error("❌ Không có dữ liệu để xuất!")
    
    with col2:
        if st.button("📊 Tải xuống CSV"):
            if st.session_state.transactions:
                df = pd.DataFrame(st.session_state.transactions)
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="💾 Tải file CSV",
                    data=csv,
                    file_name=f"thu_chi_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.error("❌ Không có dữ liệu để xuất!")

# Footer
st.markdown("---")
st.markdown("💡 **Mẹo**: Hãy nhập giao dịch thường xuyên để theo dõi tài chính hiệu quả!")
