import pytest
import uuid
from httpx import AsyncClient
from typing import Tuple, Optional # Added Optional

from app.core.config import settings
from app.models.user import User # For type hinting user from fixture
from app.schemas.hr_schemas import DesignationCreate, DesignationRead, DesignationUpdate

HR_DESIG_API_PREFIX = f"{settings.API_V1_STR}/hr/designations"

@pytest.mark.asyncio
async def test_hr_manager_can_crud_designations(
    client: AsyncClient,
    test_hr_manager_user_with_token: Tuple[User, str]
):
    hr_manager, token = test_hr_manager_user_with_token
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Designation
    desig_title = f"Lead Engineer {uuid.uuid4().hex[:4]}"
    create_payload = DesignationCreate(title=desig_title, description="Leads engineering team")
    response = await client.post(HR_DESIG_API_PREFIX + "/", json=create_payload.model_dump(), headers=headers)
    assert response.status_code == 201, response.text
    created_desig = DesignationRead(**response.json())
    assert created_desig.title == desig_title
    desig_id = created_desig.id

    # 2. Read Designation (single)
    response = await client.get(f"{HR_DESIG_API_PREFIX}/{desig_id}", headers=headers)
    assert response.status_code == 200, response.text
    read_desig = DesignationRead(**response.json())
    assert read_desig.title == desig_title

    # 3. Read Designations (list)
    response = await client.get(HR_DESIG_API_PREFIX + "/", headers=headers)
    assert response.status_code == 200, response.text
    desig_page = response.json()
    assert desig_page["total"] >= 1
    assert any(d["id"] == str(desig_id) for d in desig_page["items"])

    # 4. Update Designation
    updated_title = f"Principal Engineer {uuid.uuid4().hex[:4]}"
    update_payload = DesignationUpdate(title=updated_title, description="Updated description for Principal")
    response = await client.put(f"{HR_DESIG_API_PREFIX}/{desig_id}", json=update_payload.model_dump(exclude_unset=True), headers=headers)
    assert response.status_code == 200, response.text
    updated_desig = DesignationRead(**response.json())
    assert updated_desig.title == updated_title
    assert updated_desig.description == "Updated description for Principal"

    # 5. Delete Designation
    response = await client.delete(f"{HR_DESIG_API_PREFIX}/{desig_id}", headers=headers)
    assert response.status_code == 204, response.text # Expect 204 after router update

    # Verify deleted
    response_verify_delete = await client.get(f"{HR_DESIG_API_PREFIX}/{desig_id}", headers=headers)
    assert response_verify_delete.status_code == 404 # Not Found after delete

@pytest.mark.asyncio
async def test_hr_assistant_permissions_for_designations(
    client: AsyncClient,
    test_hr_assistant_user_with_token: Tuple[User, str],
    test_hr_manager_user_with_token: Tuple[User, str] # To create a designation to read
):
    hr_assistant, assistant_token = test_hr_assistant_user_with_token
    assistant_headers = {"Authorization": f"Bearer {assistant_token}"}

    hr_manager, manager_token = test_hr_manager_user_with_token
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    # Setup: HR Manager creates a designation
    desig_title = f"Temp Desig Assistant Test {uuid.uuid4().hex[:4]}" # Unique name
    create_payload = DesignationCreate(title=desig_title, description="Designation for assistant test")
    response_create = await client.post(HR_DESIG_API_PREFIX + "/", json=create_payload.model_dump(), headers=manager_headers)
    assert response_create.status_code == 201, response_create.text
    desig_id_str = response_create.json()["id"]

    # 1. HR Assistant CAN Read Designation (list)
    response_list = await client.get(HR_DESIG_API_PREFIX + "/", headers=assistant_headers)
    assert response_list.status_code == 200, response_list.text
    assert any(d["id"] == desig_id_str for d in response_list.json()["items"])

    # 2. HR Assistant CAN Read Designation (single)
    response_single = await client.get(f"{HR_DESIG_API_PREFIX}/{desig_id_str}", headers=assistant_headers)
    assert response_single.status_code == 200, response_single.text

    # 3. HR Assistant CANNOT Create Designation
    create_payload_assistant = DesignationCreate(title=f"Assistant Desig {uuid.uuid4().hex[:4]}")
    response_create_fail = await client.post(HR_DESIG_API_PREFIX + "/", json=create_payload_assistant.model_dump(), headers=assistant_headers)
    assert response_create_fail.status_code == 403, response_create_fail.text

    # 4. HR Assistant CANNOT Update Designation
    update_payload_assistant = DesignationUpdate(description="Assistant Update Attempt")
    response_update_fail = await client.put(f"{HR_DESIG_API_PREFIX}/{desig_id_str}", json=update_payload_assistant.model_dump(exclude_unset=True), headers=assistant_headers)
    assert response_update_fail.status_code == 403, response_update_fail.text

    # 5. HR Assistant CANNOT Delete Designation
    response_delete_fail = await client.delete(f"{HR_DESIG_API_PREFIX}/{desig_id_str}", headers=assistant_headers)
    assert response_delete_fail.status_code == 403, response_delete_fail.text

@pytest.mark.asyncio
async def test_regular_user_cannot_access_designations(
    client: AsyncClient,
    test_regular_user_with_token: Tuple[User, str],
    test_hr_manager_user_with_token: Tuple[User, str] # To create a designation
):
    regular_user, regular_token = test_regular_user_with_token
    regular_headers = {"Authorization": f"Bearer {regular_token}"}

    hr_manager, manager_token = test_hr_manager_user_with_token
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    # Setup: HR Manager creates a designation
    desig_title = f"Temp Desig Regular User Test {uuid.uuid4().hex[:4]}" # Unique name
    create_payload = DesignationCreate(title=desig_title, description="Designation for regular user test")
    response_create = await client.post(HR_DESIG_API_PREFIX + "/", json=create_payload.model_dump(), headers=manager_headers)
    assert response_create.status_code == 201, response_create.text
    desig_id_str = response_create.json()["id"]

    # Regular user tries all CRUD - all should fail (403 Forbidden)
    response_post = await client.post(HR_DESIG_API_PREFIX + "/", json=DesignationCreate(title="FailCreateDesigReg").model_dump(), headers=regular_headers)
    assert response_post.status_code == 403, response_post.text

    response_get_list = await client.get(HR_DESIG_API_PREFIX + "/", headers=regular_headers)
    assert response_get_list.status_code == 403, response_get_list.text

    response_get_single = await client.get(f"{HR_DESIG_API_PREFIX}/{desig_id_str}", headers=regular_headers)
    assert response_get_single.status_code == 403, response_get_single.text

    response_put = await client.put(f"{HR_DESIG_API_PREFIX}/{desig_id_str}", json=DesignationUpdate(title="FailUpdateDesigReg").model_dump(exclude_unset=True), headers=regular_headers)
    assert response_put.status_code == 403, response_put.text

    response_delete = await client.delete(f"{HR_DESIG_API_PREFIX}/{desig_id_str}", headers=regular_headers)
    assert response_delete.status_code == 403, response_delete.text
