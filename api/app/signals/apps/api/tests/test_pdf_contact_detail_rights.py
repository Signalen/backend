# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2022 Vereniging van Nederlandse Gemeenten, Gemeente Amsterdam

from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.views.generic.base import TemplateResponseMixin

from signals.apps.signals.factories import SignalFactory
from signals.test.utils import SIAReadWriteUserMixin, SignalsBaseApiTestCase


class TestPDFView(SIAReadWriteUserMixin, SignalsBaseApiTestCase):
    def setUp(self):
        self.signal = SignalFactory.create(reporter__email='melder@example.com')
        self.signal.reporter.email = 'melder@example.com'
        self.signal.reporter.phone = '9999999999'
        self.signal.reporter.save()

    @patch('signals.apps.api.pdf.mixins.PDFTemplateResponseMixin', TemplateResponseMixin)
    def test_can_see_contact_details(self):
        self.sia_read_write_user.user_permissions.add(Permission.objects.get(codename='sia_can_view_all_categories'))
        self.sia_read_write_user.user_permissions.add(Permission.objects.get(codename='sia_can_view_contact_details'))
        self.sia_read_write_user.refresh_from_db()

        self.client.force_authenticate(user=self.sia_read_write_user)
        url = '/signals/v1/private/signals/{}/pdf'.format(self.signal.pk)

        # We don't want to bother looking in the PDF itself, in stead we look at
        # the intermediate HTML that is rendered to PDF, hence the patch below.
        response = self.client.get(path=url)
        html = response.content.decode('utf-8')

        self.assertIn(self.signal.reporter.email, html)
        self.assertIn(self.signal.reporter.phone, html)

    @patch('signals.apps.api.pdf.mixins.PDFTemplateResponseMixin', TemplateResponseMixin)
    def test_cannot_see_contact_details(self):
        self.sia_read_write_user.user_permissions.add(Permission.objects.get(codename='sia_can_view_all_categories'))
        self.sia_read_write_user.refresh_from_db()
        self.assertFalse(self.sia_read_write_user.has_perm('signals.sia_can_view_contact_details'))

        self.client.force_authenticate(user=self.sia_read_write_user)
        url = '/signals/v1/private/signals/{}/pdf'.format(self.signal.pk)

        response = self.client.get(path=url)
        html = response.content.decode('utf-8')

        self.assertNotIn(self.signal.reporter.email, html)
        self.assertNotIn(self.signal.reporter.phone, html)
