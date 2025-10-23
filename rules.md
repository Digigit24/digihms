# PROJECT RULES & STANDARDS
# Hospital Management System - Backend Development
# Last Updated: 2025

## 🎯 PROJECT OVERVIEW
- **Project Type:** Hospital Management System
- **Framework:** Django + Django REST Framework
- **Database:** PostgreSQL (or as configured)
- **Architecture:** Modular app-based architecture
- **Current Phase:** OPD Module Implementation

---

## 📁 PROJECT STRUCTURE

### Existing Apps:
1. **patients/** - Patient management
2. **doctors/** - Doctor management
3. **appointments/** - Appointment scheduling
4. **payments/** - Online payment gateway (e-commerce focused)
5. **orders/** - Service orders (diagnostics, consultations)
6. **pharmacy/** - Pharmacy with separate cart/orders

### New App Being Built:
7. **opd/** - Outpatient Department (walk-in patients, billing, clinical notes)

---

## 🚫 STRICT RULES - NEVER VIOLATE

### 1. PERMISSIONS - CRITICAL
```
❌ NEVER create custom permission classes
❌ NEVER use: IsReceptionist, IsDoctor, IsBillingUser, etc.
✅ ALWAYS use Django's built-in Groups & Permissions system
✅ ALWAYS manage permissions via Django Admin UI
✅ ALWAYS use DjangoModelPermissions in DRF views
✅ Check permissions: request.user.has_perm('opd.add_visit')
```

**Correct Permission Implementation:**
```python
# ✅ CORRECT
from rest_framework.permissions import DjangoModelPermissions

class VisitViewSet(viewsets.ModelViewSet):
    permission_classes = [DjangoModelPermissions]
    
    def create(self, request):
        if request.user.has_perm('opd.add_visit'):
            # process
            pass

# ❌ WRONG - Never do this
class IsReceptionist(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Receptionist').exists()
```

### 2. APP BOUNDARIES - CRITICAL
```
❌ NEVER put billing in payments app
✅ OPD billing MUST be in opd app
✅ Payments app is ONLY for online payment gateways
✅ Each app handles its own domain completely
```

**Correct App Separation:**
```
opd/          → Visit management, OPD billing, clinical notes
payments/     → Online payment gateway integration only
pharmacy/     → Pharmacy orders and billing (separate)
```

### 3. MODEL RELATIONSHIPS
```
✅ Use clear ForeignKey relationships
✅ Use OneToOneField for 1:1 relationships
✅ Always add related_name for reverse lookups
✅ Use on_delete=models.PROTECT for critical data
✅ Use on_delete=models.CASCADE carefully
```

**Correct Relationship Pattern:**
```python
class Visit(models.Model):
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='opd_visits'
    )
    
class OPDBill(models.Model):
    visit = models.OneToOneField(
        Visit,
        on_delete=models.CASCADE,
        related_name='opd_bill'
    )
```

### 4. CODE STYLE
```
✅ Follow PEP 8
✅ Use meaningful variable names
✅ Add docstrings to all classes and methods
✅ Use type hints where appropriate
✅ Keep functions small and focused
✅ DRY principle - Don't Repeat Yourself
```

### 5. API DESIGN
```
✅ Use ViewSets for standard CRUD
✅ Use APIView for custom endpoints
✅ Return proper HTTP status codes
✅ Always paginate list endpoints
✅ Add filters and search capabilities
✅ Use serializers for validation
```

**Correct API Pattern:**
```python
class VisitViewSet(viewsets.ModelViewSet):
    queryset = Visit.objects.all()
    serializer_class = VisitSerializer
    permission_classes = [DjangoModelPermissions]
    filterset_fields = ['patient', 'doctor', 'status']
    search_fields = ['patient__name', 'visit_number']
    ordering_fields = ['visit_date', 'entry_time']
```

### 6. SERIALIZERS
```
✅ Create separate serializers for list/detail/create
✅ Use nested serializers for related data
✅ Add proper validation in validate_* methods
✅ Use SerializerMethodField for computed fields
```

### 7. ERROR HANDLING
```
✅ Use try-except blocks for operations
✅ Return meaningful error messages
✅ Log errors appropriately
✅ Use database transactions for critical operations
```

**Correct Error Handling:**
```python
from django.db import transaction

@transaction.atomic
def create_bill(self, request):
    try:
        # billing logic
        pass
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Bill creation failed: {e}")
        return Response(
            {'error': 'Internal error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

### 8. SIGNALS
```
✅ Use signals for cross-app communication
✅ Keep signal handlers lightweight
✅ Avoid circular imports
✅ Connect signals in apps.py ready() method
```

---

## 📋 NAMING CONVENTIONS

### Models:
```python
✅ PascalCase: Visit, OPDBill, ClinicalNote
✅ Singular names: Patient (not Patients)
✅ Descriptive: ProcedureBillItem (not BillItem)
```

### Fields:
```python
✅ snake_case: visit_date, entry_time, payment_status
✅ Boolean: is_active, has_payment, is_completed
✅ Dates: created_at, updated_at, visit_date
✅ ForeignKey: patient, doctor, visit (not patient_id)
```

### URLs:
```python
✅ kebab-case: /api/opd/visits/, /opd-bills/
✅ Plural for collections: /visits/, /bills/
✅ Nested when logical: /visits/{id}/clinical-note/
```

### Variables:
```python
✅ snake_case: visit_number, total_amount
✅ Descriptive: patient_name (not pn)
```

---

## 🏗️ MODEL FIELD STANDARDS

### Required Fields Pattern:
```python
# ID (auto)
id = models.AutoField(primary_key=True)

# Foreign Keys
patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='...')

# Choices
STATUS_CHOICES = [
    ('waiting', 'Waiting'),
    ('in_progress', 'In Progress'),
]
status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')

# Dates
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)

# Money
amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

# Files
attachment = models.FileField(upload_to='opd/attachments/%Y/%m/')

# JSON (for flexible data)
payment_details = models.JSONField(default=dict, blank=True)

# Audit
created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='...')
```

---

## 📊 SERIALIZER PATTERNS

### Standard Pattern:
```python
class VisitSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    
    class Meta:
        model = Visit
        fields = '__all__'  # or list specific fields
        read_only_fields = ['id', 'created_at', 'updated_at']

class VisitCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ['patient', 'doctor', 'visit_type']
    
    def validate_patient(self, value):
        # validation logic
        return value
```

---

## 🔒 SECURITY RULES
```
✅ ALWAYS validate user input
✅ ALWAYS use CSRF protection
✅ ALWAYS authenticate API endpoints
✅ NEVER expose sensitive data in APIs
✅ ALWAYS sanitize file uploads
✅ Use HTTPS in production
✅ Rate limit public endpoints
```

---

## 📝 DOCUMENTATION REQUIREMENTS

### Model Docstrings:
```python
class Visit(models.Model):
    """
    Represents a patient visit to OPD.
    
    Tracks the complete lifecycle from entry to discharge,
    including billing, clinical notes, and findings.
    """
```

### View Docstrings:
```python
class VisitViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing OPD visits.
    
    list: Get all visits with filters
    retrieve: Get single visit details
    create: Create new walk-in visit
    update: Update visit details
    destroy: Delete visit (soft delete preferred)
    """
```

---

## 🧪 TESTING REQUIREMENTS
```
✅ Write tests for all models
✅ Write tests for all API endpoints
✅ Write tests for utility functions
✅ Test permissions and access control
✅ Test edge cases and error scenarios
✅ Aim for >80% code coverage
```

---

## 📦 DEPENDENCIES MANAGEMENT
```
✅ Pin all package versions in requirements.txt
✅ Use virtual environment
✅ Document any system dependencies
✅ Keep dependencies minimal
```

---

## 🎨 UI/FRONTEND INTEGRATION
```
⚠️ Backend ONLY - No frontend code in this phase
✅ Design APIs with frontend in mind
✅ Return proper status codes
✅ Provide clear error messages
✅ Document all endpoints
```

---

## 🔄 WORKFLOW STANDARDS

### Visit Creation Flow:
```
1. Patient walks in / Appointment scheduled
2. Receptionist creates Visit
3. Patient added to queue
4. Doctor calls patient
5. Doctor adds clinical notes/findings
6. Billing staff creates bill
7. Payment recorded
8. Visit marked complete
```

### Billing Flow:
```
1. Visit must exist first
2. Create OPDBill (consultation) or ProcedureBill (tests)
3. Add line items (for procedures)
4. Calculate totals
5. Record payment (single or multiple modes)
6. Generate receipt
7. Update visit payment status
```

---

## 🚨 COMMON MISTAKES TO AVOID
```
❌ Creating custom permission classes
❌ Putting billing in payments app
❌ Not using transactions for financial operations
❌ Forgetting to add related_name
❌ Not validating user input
❌ Exposing sensitive data in APIs
❌ Not paginating list views
❌ Using print() instead of logging
❌ Hardcoding values instead of settings
❌ Not writing docstrings
```

---

## ✅ CHECKLIST FOR EVERY FILE

Before submitting code, verify:
- [ ] Follows project structure
- [ ] Uses Django built-in permissions (no custom)
- [ ] Has proper docstrings
- [ ] Has proper error handling
- [ ] Uses transactions where needed
- [ ] Has related_name on ForeignKeys
- [ ] Follows naming conventions
- [ ] Is properly formatted (PEP 8)
- [ ] Has no hardcoded values
- [ ] Returns proper HTTP status codes

---

## 📞 WHEN IN DOUBT

1. Check this rules file first
2. Follow Django best practices
3. Follow DRF best practices
4. Ask for clarification
5. Don't hallucinate or assume

---

## 🎯 CURRENT FOCUS

**Phase 1: Models**
- Update existing models (patients, doctors, appointments)
- Create all OPD models
- Run migrations
- Test in admin

**Next Phases:** (in order)
- Admin setup
- Utilities & signals
- Serializers
- Views
- URLs
- Groups & permissions
- Testing

---

END OF RULES FILE