import pytest
import asyncio # For asyncio.sleep
from httpx import AsyncClient
from typing import Tuple, Dict, Any, Optional # Added Optional
import uuid
from datetime import date

from app.core.config import settings
from app.models.user import User
from app.models.hr_models import Department, Designation, Employee
from app.schemas.hr_schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate, DepartmentCreate, DesignationCreate
from app.services.department_service import DepartmentService
from app.services.designation_service import DesignationService
from sqlmodel.ext.asyncio.session import AsyncSession

HR_EMP_API_PREFIX = f"{settings.API_V1_STR}/hr/employees"
HR_DEPT_API_PREFIX = f"{settings.API_V1_STR}/hr/departments"
HR_DESIG_API_PREFIX = f"{settings.API_V1_STR}/hr/designations"


@pytest_asyncio.fixture
async def hr_setup_for_employee_tests(
    client: AsyncClient,
    test_hr_manager_user_with_token: Tuple[User, str],
) -> Dict[str, Any]:
    hr_manager, token = test_hr_manager_user_with_token
    headers = {"Authorization": f"Bearer {token}"}

    dept_name = f"Test Dept EmpSetup {uuid.uuid4().hex[:4]}"
    dept_payload = DepartmentCreate(name=dept_name, description="Department for employee tests")
    response_dept = await client.post(HR_DEPT_API_PREFIX + "/", json=dept_payload.model_dump(), headers=headers)
    assert response_dept.status_code == 201, response_dept.text
    dept = DepartmentRead(**response_dept.json())

    desig_title = f"Test Desig EmpSetup {uuid.uuid4().hex[:4]}"
    desig_payload = DesignationCreate(title=desig_title, description="Designation for employee tests")
    response_desig = await client.post(HR_DESIG_API_PREFIX + "/", json=desig_payload.model_dump(), headers=headers)
    assert response_desig.status_code == 201, response_desig.text
    desig = DesignationRead(**response_desig.json())

    return {"department": dept, "designation": desig, "hr_manager_headers": headers}


@pytest.mark.asyncio
async def test_hr_manager_can_crud_employees(
    client: AsyncClient,
    hr_setup_for_employee_tests: Dict[str, Any] # This now provides headers too
):
    headers = hr_setup_for_employee_tests["hr_manager_headers"]
    dept = hr_setup_for_employee_tests["department"]
    desig = hr_setup_for_employee_tests["designation"]

    emp_email = f"employee_{uuid.uuid4().hex[:6]}@test.com"
    create_payload = EmployeeCreate(
        first_name="John", last_name="Doe", email=emp_email,
        job_title="Senior Tester", department_id=dept.id, designation_id=desig.id,
        hire_date=date.today().isoformat() # Ensure date is string for JSON
    )

    # 1. Create Employee
    response = await client.post(HR_EMP_API_PREFIX + "/", json=create_payload.model_dump(), headers=headers)
    assert response.status_code == 201, response.text
    created_emp = EmployeeRead(**response.json())
    assert created_emp.email == emp_email
    assert created_emp.department is not None and created_emp.department.id == dept.id
    assert created_emp.designation is not None and created_emp.designation.id == desig.id
    emp_id = created_emp.id

    # 2. Read Employee (single)
    response = await client.get(f"{HR_EMP_API_PREFIX}/{emp_id}", headers=headers)
    assert response.status_code == 200, response.text
    read_emp = EmployeeRead(**response.json())
    assert read_emp.email == emp_email
    assert read_emp.department is not None

    # 3. Read Employees (list & filter by department)
    response = await client.get(HR_EMP_API_PREFIX + "/", params={"department_id": str(dept.id)}, headers=headers)
    assert response.status_code == 200, response.text
    emp_page = response.json()
    assert emp_page["total"] >= 1
    assert any(e["id"] == str(emp_id) for e in emp_page["items"])

    # 4. Update Employee
    update_payload = EmployeeUpdate(job_title="Lead Tester", phone_number="123-456-7890")
    response = await client.put(f"{HR_EMP_API_PREFIX}/{emp_id}", json=update_payload.model_dump(exclude_unset=True), headers=headers)
    assert response.status_code == 200, response.text
    updated_emp = EmployeeRead(**response.json())
    assert updated_emp.job_title == "Lead Tester"
    assert updated_emp.phone_number == "123-456-7890"

    # 5. Delete Employee
    response = await client.delete(f"{HR_EMP_API_PREFIX}/{emp_id}", headers=headers)
    assert response.status_code == 204, response.text # Expecting 204 after router update

    # Verify deleted
    response_verify_delete = await client.get(f"{HR_EMP_API_PREFIX}/{emp_id}", headers=headers)
    assert response_verify_delete.status_code == 404

@pytest.mark.asyncio
async def test_hr_assistant_permissions_for_employees(
    client: AsyncClient,
    test_hr_assistant_user_with_token: Tuple[User, str],
    hr_setup_for_employee_tests: Dict[str, Any] # Provides dept, desig, and manager headers for setup
):
    hr_assistant, assistant_token = test_hr_assistant_user_with_token
    assistant_headers = {"Authorization": f"Bearer {assistant_token}"}
    manager_headers = hr_setup_for_employee_tests["hr_manager_headers"] # Use manager to setup employee

    dept = hr_setup_for_employee_tests["department"]
    desig = hr_setup_for_employee_tests["designation"]

    # Setup: HR Manager creates an employee
    emp_email_setup = f"emp_for_assistant_{uuid.uuid4().hex[:6]}@test.com"
    create_payload_manager = EmployeeCreate(
        first_name="Setup", last_name="User", email=emp_email_setup,
        department_id=dept.id, designation_id=desig.id, hire_date=date.today().isoformat()
    )
    response_create_mgr = await client.post(HR_EMP_API_PREFIX + "/", json=create_payload_manager.model_dump(), headers=manager_headers)
    assert response_create_mgr.status_code == 201, response_create_mgr.text
    emp_id_setup_str = response_create_mgr.json()["id"]

    # 1. HR Assistant CAN Create Employee
    emp_email_assistant = f"emp_by_assistant_{uuid.uuid4().hex[:6]}@test.com"
    create_payload_assistant = EmployeeCreate(
        first_name="AssistantCreated", last_name="User", email=emp_email_assistant,
        department_id=dept.id, designation_id=desig.id, hire_date=date.today().isoformat()
    )
    response_create_asst = await client.post(HR_EMP_API_PREFIX + "/", json=create_payload_assistant.model_dump(), headers=assistant_headers)
    assert response_create_asst.status_code == 201, response_create_asst.text

    # 2. HR Assistant CAN Read Employee (list)
    response_list = await client.get(HR_EMP_API_PREFIX + "/", headers=assistant_headers)
    assert response_list.status_code == 200, response_list.text
    assert any(e["id"] == emp_id_setup_str for e in response_list.json()["items"])

    # 3. HR Assistant CAN Read Employee (single)
    response_single = await client.get(f"{HR_EMP_API_PREFIX}/{emp_id_setup_str}", headers=assistant_headers)
    assert response_single.status_code == 200, response_single.text

    # 4. HR Assistant CANNOT Update Employee
    update_payload_assistant = EmployeeUpdate(job_title="Assistant Update Attempt")
    response_update_fail = await client.put(f"{HR_EMP_API_PREFIX}/{emp_id_setup_str}", json=update_payload_assistant.model_dump(exclude_unset=True), headers=assistant_headers)
    assert response_update_fail.status_code == 403, response_update_fail.text

    # 5. HR Assistant CANNOT Delete Employee
    response_delete_fail = await client.delete(f"{HR_EMP_API_PREFIX}/{emp_id_setup_str}", headers=assistant_headers)
    assert response_delete_fail.status_code == 403, response_delete_fail.text

@pytest.mark.asyncio
async def test_regular_user_cannot_access_employees(
    client: AsyncClient,
    test_regular_user_with_token: Tuple[User, str],
    hr_setup_for_employee_tests: Dict[str, Any] # Provides dept, desig, and manager headers for setup
):
    regular_user, regular_token = test_regular_user_with_token
    regular_headers = {"Authorization": f"Bearer {regular_token}"}
    manager_headers = hr_setup_for_employee_tests["hr_manager_headers"]

    dept = hr_setup_for_employee_tests["department"]
    desig = hr_setup_for_employee_tests["designation"]

    # Setup: HR Manager creates an employee
    emp_email_setup = f"emp_for_regular_{uuid.uuid4().hex[:6]}@test.com"
    create_payload_manager = EmployeeCreate(
        first_name="Setup", last_name="UserReg", email=emp_email_setup,
        department_id=dept.id, designation_id=desig.id, hire_date=date.today().isoformat()
    )
    response_create_mgr = await client.post(HR_EMP_API_PREFIX + "/", json=create_payload_manager.model_dump(), headers=manager_headers)
    assert response_create_mgr.status_code == 201, response_create_mgr.text
    emp_id_setup_str = response_create_mgr.json()["id"]

    # Regular user tries all CRUD - all should fail (403)
    emp_email_regular = f"emp_by_regular_{uuid.uuid4().hex[:6]}@test.com"
    create_payload_regular = EmployeeCreate(first_name="Fail", last_name="Create", email=emp_email_regular, hire_date=date.today().isoformat())
    response_post = await client.post(HR_EMP_API_PREFIX + "/", json=create_payload_regular.model_dump(), headers=regular_headers)
    assert response_post.status_code == 403, response_post.text

    response_get_list = await client.get(HR_EMP_API_PREFIX + "/", headers=regular_headers)
    assert response_get_list.status_code == 403, response_get_list.text

    response_get_single = await client.get(f"{HR_EMP_API_PREFIX}/{emp_id_setup_str}", headers=regular_headers)
    assert response_get_single.status_code == 403, response_get_single.text

    update_payload_regular = EmployeeUpdate(job_title="Fail Update")
    response_put = await client.put(f"{HR_EMP_API_PREFIX}/{emp_id_setup_str}", json=update_payload_regular.model_dump(exclude_unset=True), headers=regular_headers)
    assert response_put.status_code == 403, response_put.text

    response_delete = await client.delete(f"{HR_EMP_API_PREFIX}/{emp_id_setup_str}", headers=regular_headers)
    assert response_delete.status_code == 403, response_delete.text
