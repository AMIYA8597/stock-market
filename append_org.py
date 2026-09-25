import sys

with open('backend/app/api/v1/organizations.py', 'a', encoding='utf-8') as f:
    f.write('''
class OrganizationCreate(BaseModel):
    name: str
    slug: str

@router.post("", response_model=OrganizationResponse)
async def create_organization(
    payload: OrganizationCreate,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    user_id = uuid.UUID(ctx.user_id)
    org = Organization(name=payload.name, slug=payload.slug)
    db.add(org)
    await db.flush()
    member = OrgMember(organization_id=org.id, user_id=user_id, role="OWNER", status="active")
    db.add(member)
    await db.commit()
    return OrganizationResponse(id=str(org.id), name=org.name, slug=org.slug, role="OWNER")
''')
