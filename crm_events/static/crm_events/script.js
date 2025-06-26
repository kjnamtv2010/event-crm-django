// crm_events/static/crm_events/script.js

$(document).ready(function() {
    const userListBody = $('#userListBody'); // <-- Thay đổi ID ở đây
    const loadingMessage = $('#loadingMessage');
    const noUsersMessage = $('#noUsersMessage');

    // ... (các biến filter, button, pagination khác không thay đổi) ...
    const companyFilter = $('#companyFilter');
    const jobTitleFilter = $('#jobTitleFilter');
    const cityFilter = $('#cityFilter');
    const stateFilter = $('#stateFilter');
    const hostingMin = $('#hostingMin');
    const hostingMax = $('#hostingMax');
    const registeredMin = $('#registeredMin');
    const registeredMax = $('#registeredMax');
    const sortBy = $('#sortBy');

    const applyFiltersBtn = $('#applyFilters');
    const clearFiltersBtn = $('#clearFilters');

    const prevPageBtn = $('#prevPage');
    const nextPageBtn = $('#nextPage');
    const pageInfoSpan = $('#pageInfo');
    const pageSizeSelect = $('#pageSizeSelect');

    let currentPage = 1;
    let currentFilters = {};
    let currentOrdering = sortBy.val();
    let currentPageSize = pageSizeSelect.val();
    let totalPages = 1;

    const API_BASE_URL = '/api/crm/users/';

    async function fetchUsers() {
        loadingMessage.show();
        noUsersMessage.hide();
        userListBody.empty(); // <-- Xóa nội dung của tbody

        const filters = {
            ...currentFilters,
            page: currentPage,
            page_size: currentPageSize,
            ordering: currentOrdering
        };

        const queryParams = new URLSearchParams(filters).toString();
        const url = `${API_BASE_URL}?${queryParams}`;

        try {
            const response = await fetch(url);
            if (!response.ok) {
                const errorData = await response.json();
                const errorMessage = errorData.error || `HTTP error! status: ${response.status}`;
                throw new Error(errorMessage);
            }
            const data = await response.json();

            loadingMessage.hide();

            if (data.results && data.results.length > 0) {
                renderUsers(data.results);
            } else {
                noUsersMessage.show();
            }

            updatePagination(data.next, data.previous, data.count);

        } catch (error) {
            console.error("Error fetching users:", error);
            loadingMessage.hide();
            userListBody.html(`<tr><td colspan="8" class="error-message">Error loading users: ${error.message}. Please try again.</td></tr>`); // Dùng colspan để thông báo lỗi trải hết bảng
            noUsersMessage.hide();
            prevPageBtn.prop('disabled', true);
            nextPageBtn.prop('disabled', true);
            pageInfoSpan.text('Error');
        }
    }

    function renderUsers(users) {
        userListBody.empty(); // Đảm bảo làm rỗng tbody trước khi thêm hàng mới
        users.forEach(user => {
            const userRow = `
                <tr>
                    <td>${user.username}</td>
                    <td>${user.email || 'N/A'}</td>
                    <td>${user.company || 'N/A'}</td>
                    <td>${user.job_title || 'N/A'}</td>
                    <td>${user.city || 'N/A'}, ${user.state || 'N/A'}</td>
                    <td>${user.total_hosting_events}</td>
                    <td>${user.total_registered_events}</td>
                    <td>${new Date(user.date_joined).toLocaleDateString()}</td>
                </tr>
            `;
            userListBody.append(userRow);
        });
    }

    // ... (các hàm updatePagination, collectFilters, applyFilters, clearFilters và Event Listeners không thay đổi) ...

    function updatePagination(nextUrl, prevUrl, totalCount) {
        prevPageBtn.prop('disabled', !prevUrl);
        nextPageBtn.prop('disabled', !nextUrl);

        totalPages = Math.ceil(totalCount / currentPageSize);
        pageInfoSpan.text(`Page ${currentPage} of ${totalPages} (Total: ${totalCount})`);
    }

    function collectFilters() {
        const filters = {};
        if (companyFilter.val()) filters.company = companyFilter.val();
        if (jobTitleFilter.val()) filters.job_title = jobTitleFilter.val();
        if (cityFilter.val()) filters.city = cityFilter.val();
        if (stateFilter.val()) filters.state = stateFilter.val();

        if (hostingMin.val()) filters.total_hosting_events_min = hostingMin.val();
        if (hostingMax.val()) filters.total_hosting_events_max = hostingMax.val();
        if (registeredMin.val()) filters.total_registered_events_min = registeredMin.val();
        if (registeredMax.val()) filters.total_registered_events_max = registeredMax.val();

        return filters;
    }

    function applyFilters() {
        currentPage = 1;
        currentFilters = collectFilters();
        currentOrdering = sortBy.val();
        fetchUsers();
    }

    function clearFilters() {
        companyFilter.val('');
        jobTitleFilter.val('');
        cityFilter.val('');
        stateFilter.val('');
        hostingMin.val('');
        hostingMax.val('');
        registeredMin.val('');
        registeredMax.val('');
        sortBy.val('username');
        pageSizeSelect.val('10');
        applyFilters();
    }

    // Event Listeners (Dùng .on('click', ...) thay vì .addEventListener('click', ...))
    applyFiltersBtn.on('click', applyFilters);
    clearFiltersBtn.on('click', clearFilters);

    prevPageBtn.on('click', () => {
        if (currentPage > 1) {
            currentPage--;
            fetchUsers();
        }
    });

    nextPageBtn.on('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            fetchUsers();
        }
    });

    pageSizeSelect.on('change', () => {
        currentPageSize = pageSizeSelect.val();
        currentPage = 1;
        fetchUsers();
    });

    sortBy.on('change', () => {
        currentOrdering = sortBy.val();
        currentPage = 1;
        fetchUsers();
    });

    // Initial load
    fetchUsers();
});