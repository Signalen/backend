import logging

from datapunt_api.rest import DisplayField, HALSerializer
from django.core.exceptions import ValidationError
from django.forms import ImageField
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from signals.apps.signals import workflow
from signals.apps.signals.fields import (
    CategoryLinksField,
    MainCategoryHyperlinkedIdentityField,
    PriorityLinksField,
    SignalLinksField,
    SignalUnauthenticatedLinksField,
    StatusLinksField,
    SubCategoryHyperlinkedIdentityField,
    SubCategoryHyperlinkedRelatedField
)
from signals.apps.signals.mixins import AddExtrasMixin
from signals.apps.signals.models import (
    CategoryAssignment,
    Department,
    Location,
    MainCategory,
    Priority,
    Reporter,
    Signal,
    Status,
    SubCategory
)
from signals.apps.signals.validators import NearAmsterdamValidatorMixin

logger = logging.getLogger(__name__)


class SignalUpdateImageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(label='ID', read_only=True)
    signal_id = serializers.CharField(label='SIGNAL_ID')

    class Meta(object):
        model = Signal
        fields = (
            'id',
            'signal_id',
            'image'
        )

    def create(self, validated_data):
        signal_id = validated_data.get('signal_id')
        instance = Signal.objects.get(signal_id=signal_id)
        return self.update(instance, validated_data)

    def validate(self, attrs):
        # self.data.is_valid()
        image = self.initial_data.get('image', False)
        if image:
            if image.size > 8388608:  # 8MB = 8*1024*1024
                raise ValidationError("Foto mag maximaal 8Mb groot zijn.")
        else:
            raise ValidationError("Foto is een verplicht veld.")

        return attrs

    def update(self, instance, validated_data):
        image = validated_data['image']

        # Only allow adding a photo if none is set.
        if instance.image:
            raise PermissionDenied("Melding is reeds van foto voorzien.")

        if image:
            setattr(instance, 'image', image)
            instance.save()

        return instance


class _NestedLocationModelSerializer(NearAmsterdamValidatorMixin, serializers.ModelSerializer):

    class Meta:
        model = Location
        geo_field = 'geometrie'
        fields = (
            'id',
            'stadsdeel',
            'buurt_code',
            'address',
            'address_text',
            'geometrie',
            'extra_properties',
        )
        read_only_fields = (
            'id',
        )
        extra_kwargs = {
            'id': {'label': 'ID', },
        }


class _NestedStatusModelSerializer(serializers.ModelSerializer):
    state_display = serializers.CharField(source='get_state_display', read_only=True)

    class Meta:
        model = Status
        fields = (
            'text',
            'user',
            'state',
            'state_display',
            'extra_properties',
            'created_at',
        )
        read_only_fields = (
            'state',
            'created_at',
        )


class _NestedCategoryModelSerializer(serializers.ModelSerializer):
    # Should be required, but to make it work with the backwards compatibility fix it's not required
    # at the moment..
    sub_category = SubCategoryHyperlinkedRelatedField(write_only=True, required=False)

    sub = serializers.CharField(source='sub_category.name', read_only=True)
    sub_slug = serializers.CharField(source='sub_category.slug', read_only=True)
    main = serializers.CharField(source='sub_category.main_category.name', read_only=True)
    main_slug = serializers.CharField(source='sub_category.main_category.slug', read_only=True)

    class Meta:
        model = CategoryAssignment
        fields = (
            'sub',
            'sub_slug',
            'main',
            'main_slug',
            'sub_category',
        )

    def to_internal_value(self, data):
        internal_data = super().to_internal_value(data)

        # Backwards compatibility fix to let this endpoint work with `sub` as key.
        is_main_name_posted = 'main' in data
        is_sub_name_posted = 'sub' in data
        is_sub_category_not_posted = 'sub_category' not in data
        if is_main_name_posted and is_sub_name_posted and is_sub_category_not_posted:
            try:
                sub_category = SubCategory.objects.get(main_category__name=data['main'],
                                                       name=data['sub'])
            except SubCategory.DoesNotExist:
                pass
            else:
                internal_data['sub_category'] = sub_category

        return internal_data


class _NestedReporterModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Reporter
        fields = (
            'email',
            'phone',
            'extra_properties',
        )


class _NestedPriorityModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Priority
        fields = (
            'priority',
        )

#
# Unauth serializers
#


class SignalCreateSerializer(AddExtrasMixin, serializers.ModelSerializer):
    location = _NestedLocationModelSerializer()
    reporter = _NestedReporterModelSerializer()
    status = _NestedStatusModelSerializer()
    category = _NestedCategoryModelSerializer(source='category_assignment')
    priority = _NestedPriorityModelSerializer(required=False, read_only=True)

    incident_date_start = serializers.DateTimeField()

    class Meta(object):
        model = Signal
        fields = (
            'id',
            'signal_id',
            'source',
            'text',
            'text_extra',
            'status',
            'location',
            'category',
            'reporter',
            'priority',
            'created_at',
            'updated_at',
            'incident_date_start',
            'incident_date_end',
            'operational_date',
            'image',
            'extra_properties',
        )
        read_only_fields = (
            'id',
            'signal_id',
            'created_at',
            'updated_at',
        )
        extra_kwargs = {
            'id': {'label': 'ID'},
            'signal_id': {'label': 'SIGNAL_ID'},
        }

    def create(self, validated_data):
        validated_data = self.add_extra_properties(validated_data)
        validated_data = self.add_user(validated_data)

        status_data = validated_data.pop('status')
        location_data = validated_data.pop('location')
        reporter_data = validated_data.pop('reporter')
        category_assignment_data = validated_data.pop('category_assignment')
        signal = Signal.actions.create_initial(
            validated_data, location_data, status_data, category_assignment_data, reporter_data)
        return signal

    def validate(self, data):
        image = self.initial_data.get('image', False)
        if image:
            if image.size > 8388608:  # 8MB = 8*1024*1024
                raise ValidationError("Maximum photo size is 3Mb.")

        return data


class _NestedStatusUnauthenticatedModelSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(label='ID', read_only=True)

    class Meta:
        model = Status
        fields = (
            'id',
            'state',
        )
        extra_kwargs = {
            '_signal': {'required': False},
        }


class SignalStatusOnlyHALSerializer(HALSerializer):
    _display = DisplayField()
    signal_id = serializers.CharField(label='SIGNAL_ID', read_only=True)
    status = _NestedStatusUnauthenticatedModelSerializer(read_only=True)

    _links = SignalUnauthenticatedLinksField('signal-detail')

    class Meta(object):
        model = Signal
        fields = (
            '_links',
            '_display',
            'signal_id',
            'status',
            'created_at',
            'updated_at',
            'incident_date_start',
            'incident_date_end',
            'operational_date',
        )
        read_only_fields = (
            'created_at',
            'updated_at',
        )


#
# Auth serializers
#

class SignalAuthHALSerializer(HALSerializer):
    _display = DisplayField()
    id = serializers.IntegerField(label='ID', read_only=True)
    signal_id = serializers.CharField(label='SIGNAL_ID', read_only=True)
    location = _NestedLocationModelSerializer(read_only=True)
    reporter = _NestedReporterModelSerializer(read_only=True)
    status = _NestedStatusModelSerializer(read_only=True)
    category = _NestedCategoryModelSerializer(source='category_assignment', read_only=True)
    priority = _NestedPriorityModelSerializer(read_only=True)

    image = ImageField(max_length=50, allow_empty_file=False)

    serializer_url_field = SignalLinksField

    class Meta(object):
        model = Signal
        fields = (
            '_links',
            '_display',
            'id',
            'signal_id',
            'source',
            'text',
            'text_extra',
            'status',
            'location',
            'category',
            'reporter',
            'priority',
            'created_at',
            'updated_at',
            'incident_date_start',
            'incident_date_end',
            'operational_date',
            'image',
            'extra_properties',
        )
        read_only_fields = (
            'id',
            'signal_id',
            'created_at',
            'updated_at',
        )


class LocationHALSerializer(NearAmsterdamValidatorMixin, HALSerializer):
    _signal = serializers.PrimaryKeyRelatedField(queryset=Signal.objects.all())

    class Meta:
        model = Location
        fields = (
            'id',
            '_signal',
            'stadsdeel',
            'buurt_code',
            'address',
            'geometrie',
            'extra_properties',
        )

    def create(self, validated_data):
        signal = validated_data.pop('_signal')
        location = Signal.actions.update_location(validated_data, signal)
        return location


class StatusHALSerializer(AddExtrasMixin, HALSerializer):
    _display = DisplayField()
    _signal = serializers.PrimaryKeyRelatedField(queryset=Signal.objects.all())
    serializer_url_field = StatusLinksField
    state_display = serializers.CharField(source='get_state_display', read_only=True)

    class Meta(object):
        model = Status
        fields = (
            '_links',
            '_display',
            '_signal',
            'text',
            'user',
            'state',
            'state_display',
            'extra_properties',
            'created_at',
        )
        extra_kwargs = {
            'state': {'choices': workflow.STATUS_CHOICES_API}
        }

    def create(self, validated_data):
        validated_data = self.add_extra_properties(validated_data)
        validated_data = self.add_user(validated_data)

        signal = validated_data.pop('_signal')
        status = Signal.actions.update_status(validated_data, signal)
        return status

    def validate(self, data):
        try:
            status = Status(**data)
            status.clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.error_dict)

        return data


class CategoryHALSerializer(HALSerializer):
    serializer_url_field = CategoryLinksField
    _display = DisplayField()

    _signal = serializers.PrimaryKeyRelatedField(queryset=Signal.objects.all())

    # Should be required, but to make it work with the backwards compatibility fix it's not required
    # at the moment..
    sub_category = SubCategoryHyperlinkedRelatedField(write_only=True, required=False)

    sub = serializers.CharField(source='sub_category.name', read_only=True)
    sub_slug = serializers.CharField(source='sub_category.slug', read_only=True)
    main = serializers.CharField(source='sub_category.main_category.name', read_only=True)
    main_slug = serializers.CharField(source='sub_category.main_category.slug', read_only=True)

    class Meta(object):
        model = CategoryAssignment
        fields = (
            '_links',
            '_display',
            '_signal',
            'sub_category',
            'sub',
            'sub_slug',
            'main',
            'main_slug',
        )

    def to_internal_value(self, data):
        internal_data = super().to_internal_value(data)

        # Backwards compatibility fix to let this endpoint work with `sub` as key.
        is_main_name_posted = 'main' in data
        is_sub_name_posted = 'sub' in data
        is_sub_category_not_posted = 'sub_category' not in data
        if is_main_name_posted and is_sub_name_posted and is_sub_category_not_posted:
            try:
                sub_category = SubCategory.objects.get(main_category__name=data['main'],
                                                       name=data['sub'])
            except SubCategory.DoesNotExist:
                pass
            else:
                internal_data['sub_category'] = sub_category

        return internal_data

    def create(self, validated_data):
        signal = validated_data.pop('_signal')
        category = Signal.actions.update_category_assignment(validated_data, signal)
        return category


class PriorityHALSerializer(HALSerializer):
    _display = DisplayField()
    _signal = serializers.PrimaryKeyRelatedField(queryset=Signal.objects.all())
    serializer_url_field = PriorityLinksField

    class Meta:
        model = Priority
        fields = (
            '_links',
            '_display',
            'id',
            '_signal',
            'priority',
        )

    def create(self, validated_data):
        signal = validated_data.pop('_signal')
        priority = Signal.actions.update_priority(validated_data, signal)
        return priority


#
# Category terms
#

class _NestedDepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department
        fields = (
            'code',
            'name',
            'is_intern',
        )


class SubCategoryHALSerializer(HALSerializer):
    serializer_url_field = SubCategoryHyperlinkedIdentityField
    _display = DisplayField()
    departments = _NestedDepartmentSerializer(many=True)

    class Meta:
        model = SubCategory
        fields = (
            '_links',
            '_display',
            'name',
            'slug',
            'handling',
            'departments',
        )


class MainCategoryHALSerializer(HALSerializer):
    serializer_url_field = MainCategoryHyperlinkedIdentityField
    _display = DisplayField()
    sub_categories = SubCategoryHALSerializer(many=True)

    class Meta:
        model = MainCategory
        fields = (
            '_links',
            '_display',
            'name',
            'slug',
            'sub_categories',
        )
