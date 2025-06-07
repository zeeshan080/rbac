import pytest
import uuid
from httpx import AsyncClient
from typing import Tuple, Optional # Added Optional for type hint

from app.core.config import settings
from app.models.user import User # For type hinting user from fixture
from app.schemas.hr_schemas import DepartmentCreate, DepartmentRead, DepartmentUpdate

HR_DEPT_API_PREFIX = f"{settings.API_V1_STR}/hr/departments"

@pytest.mark.asyncio
async def test_hr_manager_can_crud_departments(
    client: AsyncClient,
    test_hr_manager_user_with_token: Tuple[User, str]
):
    hr_manager, token = test_hr_manager_user_with_token
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Department
    dept_name = f"Engineering Dept {uuid.uuid4().hex[:4]}"
    create_payload = DepartmentCreate(name=dept_name, description="Core engineering functions")
    response = await client.post(HR_DEPT_API_PREFIX + "/", json=create_payload.model_dump(), headers=headers)
    assert response.status_code == 201, response.text
    created_dept = DepartmentRead(**response.json())
    assert created_dept.name == dept_name
    dept_id = created_dept.id

    # 2. Read Department (single)
    response = await client.get(f"{HR_DEPT_API_PREFIX}/{dept_id}", headers=headers)
    assert response.status_code == 200, response.text
    read_dept = DepartmentRead(**response.json())
    assert read_dept.name == dept_name

    # 3. Read Departments (list)
    response = await client.get(HR_DEPT_API_PREFIX + "/", headers=headers)
    assert response.status_code == 200, response.text
    dept_page = response.json()
    assert dept_page["total"] >= 1 # Check if total is at least 1
    assert any(d["id"] == str(dept_id) for d in dept_page["items"])

    # 4. Update Department
    updated_name = f"Advanced Engineering {uuid.uuid4().hex[:4]}"
    update_payload = DepartmentUpdate(name=updated_name, description="Updated description")
    response = await client.put(f"{HR_DEPT_API_PREFIX}/{dept_id}", json=update_payload.model_dump(exclude_unset=True), headers=headers)
    assert response.status_code == 200, response.text
    updated_dept = DepartmentRead(**response.json())
    assert updated_dept.name == updated_name
    assert updated_dept.description == "Updated description"

    # 5. Delete Department
    response = await client.delete(f"{HR_DEPT_API_PREFIX}/{dept_id}", headers=headers)
    assert response.status_code == 204, response.text # Department router returns 204

    # Verify deleted
    response_verify_delete = await client.get(f"{HR_DEPT_API_PREFIX}/{dept_id}", headers=headers)
    assert response_verify_delete.status_code == 404 # Not Found after delete

@pytest.mark.asyncio
async def test_hr_assistant_permissions_for_departments(
    client: AsyncClient,
    test_hr_assistant_user_with_token: Tuple[User, str],
    test_hr_manager_user_with_token: Tuple[User, str] # To create a department to read
):
    hr_assistant, assistant_token = test_hr_assistant_user_with_token
    assistant_headers = {"Authorization": f"Bearer {assistant_token}"}

    hr_manager, manager_token = test_hr_manager_user_with_token
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    # Setup: HR Manager creates a department
    dept_name = f"Temp Dept Assistant Test {uuid.uuid4().hex[:4]}" # More unique name
    create_payload = DepartmentCreate(name=dept_name, description="Department for assistant test")
    response_create = await client.post(HR_DEPT_API_PREFIX + "/", json=create_payload.model_dump(), headers=manager_headers)
    assert response_create.status_code == 201, response_create.text
    dept_id_str = response_create.json()["id"] # Get ID as string for comparisons in list

    # 1. HR Assistant CAN Read Department (list)
    response_list = await client.get(HR_DEPT_API_PREFIX + "/", headers=assistant_headers)
    assert response_list.status_code == 200, response_list.text
    assert any(d["id"] == dept_id_str for d in response_list.json()["items"])

    # 2. HR Assistant CAN Read Department (single)
    response_single = await client.get(f"{HR_DEPT_API_PREFIX}/{dept_id_str}", headers=assistant_headers)
    assert response_single.status_code == 200, response_single.text

    # 3. HR Assistant CANNOT Create Department
    create_payload_assistant = DepartmentCreate(name=f"Assistant Dept {uuid.uuid4().hex[:4]}")
    response_create_fail = await client.post(HR_DEPT_API_PREFIX + "/", json=create_payload_assistant.model_dump(), headers=assistant_headers)
    assert response_create_fail.status_code == 403, response_create_fail.text

    # 4. HR Assistant CANNOT Update Department
    update_payload_assistant = DepartmentUpdate(description="Assistant Update Attempt")
    response_update_fail = await client.put(f"{HR_DEPT_API_PREFIX}/{dept_id_str}", json=update_payload_assistant.model_dump(exclude_unset=True), headers=assistant_headers)
    assert response_update_fail.status_code == 403, response_update_fail.text

    # 5. HR Assistant CANNOT Delete Department
    response_delete_fail = await client.delete(f"{HR_DEPT_API_PREFIX}/{dept_id_str}", headers=assistant_headers)
    assert response_delete_fail.status_code == 403, response_delete_fail.text

@pytest.mark.asyncio
async def test_regular_user_cannot_access_departments(
    client: AsyncClient,
    test_regular_user_with_token: Tuple[User, str],
    test_hr_manager_user_with_token: Tuple[User, str] # To create a department
):
    regular_user, regular_token = test_regular_user_with_token
    regular_headers = {"Authorization": f"Bearer {regular_token}"}

    hr_manager, manager_token = test_hr_manager_user_with_token
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    # Setup: HR Manager creates a department
    dept_name = f"Temp Dept Regular User Test {uuid.uuid4().hex[:4]}" # More unique name
    create_payload = DepartmentCreate(name=dept_name, description="Department for regular user test")
    response_create = await client.post(HR_DEPT_API_PREFIX + "/", json=create_payload.model_dump(), headers=manager_headers)
    assert response_create.status_code == 201, response_create.text
    dept_id_str = response_create.json()["id"]

    # Regular user tries all CRUD - all should fail (403 Forbidden)
    response_post = await client.post(HR_DEPT_API_PREFIX + "/", json=DepartmentCreate(name="FailCreateReg").model_dump(), headers=regular_headers)
    assert response_post.status_code == 403, response_post.text

    response_get_list = await client.get(HR_DEPT_API_PREFIX + "/", headers=regular_headers)
    assert response_get_list.status_code == 403, response_get_list.text

    response_get_single = await client.get(f"{HR_DEPT_API_PREFIX}/{dept_id_str}", headers=regular_headers)
    assert response_get_single.status_code == 403, response_get_single.text

    response_put = await client.put(f"{HR_DEPT_API_PREFIX}/{dept_id_str}", json=DepartmentUpdate(name="FailUpdateReg").model_dump(exclude_unset=True), headers=regular_headers)
    assert response_put.status_code == 403, response_put.text

    response_delete = await client.delete(f"{HR_DEPT_API_PREFIX}/{dept_id_str}", headers=regular_headers)
    assert response_delete.status_code == 403, response_delete.text
