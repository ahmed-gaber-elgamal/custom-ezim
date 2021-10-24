# -*- coding: utf-8 -*-
from odoo import http, tools, _
from odoo.http import request
from werkzeug.exceptions import Forbidden
from odoo.addons.ezim.controllers.main import CheckCompatibility
from odoo.addons.ezim.controllers.main import NewNumberForm


class CheckCompatibility(CheckCompatibility):
    @http.route('/compatibility/request', website=True, auth='public', type="http")
    def compatibility_request(self, **kw):
        error = dict()
        error_message = []
        required_fields = ['imei', 'phone_ch', 'email']

        for field_name in required_fields:
            if not kw.get(field_name):
                error[field_name] = 'missing'

        # from odoo import tools
        if kw.get('email') and not tools.single_email_re.match(kw.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        if len(kw.get('imei')) != 15 or not kw.get('imei').isdigit():
            error["imei"] = 'error'
            error_message.append(_('Provide a Valid IMEI Number'))

        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        if error:
            error['error_message'] = error_message

        req_compat = {
            'imei': kw.get('imei'),
            'phone_model': kw.get('phone_model'),
            'phone_ch': kw.get('phone_ch'),
            'email': kw.get('email'),

        }

        if error_message:
            return request.render("ezim.ezsim_check_compatibility_temp", {'errors': error})
        else:
            request.env['check.compatibility'].create(req_compat)
            return request.render("ezim.request_thanks", {})


class NewNumberForm(NewNumberForm):
    @http.route('/compatibility/new_number', type='http', methods=['GET', 'POST'], auth="public", website=True,
                csrf=False)
    def new_number_form(self, **kw):
        if kw.get('id'):
            registration = kw.get('id')
            sim_order_id = request.env['product.product'].sudo().browse(
                int(registration))
            sale_order = request.website.sale_get_order(force_create=True)

            sale_order._cart_update(
                product_id=(sim_order_id.id),
                add_qty=1,

            )
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order()

        mode = (False, False)
        can_edit_vat = False
        def_country_id = order.partner_id.country_id
        values, errors = {}, {}

        partner_id = int(kw.get('partner_id', -1))

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            mode = ('new', 'billing')
            can_edit_vat = False
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                def_country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id

        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    mode = ('edit', 'billing')
                    print("edit/billing")
                    can_edit_vat = order.partner_id.can_edit_vat()
                else:
                    shippings = Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                        print("shippig1")
                    else:
                        return Forbidden()
                if mode:
                    values = Partner.browse(partner_id)
            elif partner_id == -1:
                mode = ('new', 'shipping')

            else:  # no mode - refresh without post?
                return request.redirect('/shop/checkout')

        # IF POSTED
        if 'submitted' in kw:
            pre_values = self.values_preprocess(order, mode, kw)
            errors, error_msg = self.checkout_form_validate(mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(order, mode, pre_values, errors, error_msg)

            new_number_request = []
            if kw.get('activation_date'):
                # if customer:

                request.env['buy.new_sim'].create({

                    'name': kw.get('name'),
                    'email': kw.get('email'),
                    'phone': kw.get('phone'),
                    'activation_date': kw.get('activation_date'),
                    'order_no': order.id,
                    'order_name': order.id,
                    'partner_id': order.partner_id.id,
                })
                sim_order_id = request.env['product.product'].sudo().search([('is_sim', '=', True)])
                sale_order = request.website.sale_get_order(force_create=True)
                if sim_order_id:
                    sale_order._cart_update(
                        product_id=int(sim_order_id.id),
                        add_qty=1,
                    )

            else:
                if errors:
                    errors['error_message'] = error_msg
                country = 'country_id' in values and values['country_id'] != '' and request.env['res.country'].browse(
                    int(values['country_id']))
                country = country and country.exists() or def_country_id
                render_values = {
                    'website_sale_order': order,
                    'partner_id': partner_id,
                    'mode': mode,
                    'checkout': values,
                    'can_edit_vat': can_edit_vat,
                    'country': country,
                    'countries': country.get_website_sale_countries(mode=mode[1]),
                    "states": country.get_website_sale_states(mode=mode[1]),
                    'error': errors,
                    'callback': kw.get('callback'),
                    'only_services': order and order.only_services,
                }

                return request.render("ezim.ezsim_new_sim_form", render_values)

            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                partner_id = self._checkout_form_save(mode, post, kw)
                if mode[1] == 'billing':
                    order.partner_id = partner_id
                    order.with_context(not_self_saleperson=True).onchange_partner_id()
                    # This is the *only* thing that the front end user will see/edit anyway when choosing billing address
                    order.partner_invoice_id = partner_id
                    if not kw.get('use_same'):
                        kw['callback'] = kw.get('callback') or \
                                         (not order.only_services and (
                                                 mode[0] == 'edit' and '/shop/checkout' or '/compatibility/new_number'))
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id

                order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]
                if not errors:
                    return request.redirect(kw.get('callback') or '/shop/confirm_orders')

        country = 'country_id' in values and values['country_id'] != '' and request.env['res.country'].browse(
            int(values['country_id']))
        country = country and country.exists() or def_country_id
        render_values = {
            'website_sale_order': order,
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'can_edit_vat': can_edit_vat,
            'country': country,
            'countries': country.get_website_sale_countries(mode=mode[1]),
            "states": country.get_website_sale_states(mode=mode[1]),
            'error': errors,
            'callback': kw.get('callback'),
            'only_services': order and order.only_services,
        }

        return request.render("ezim.ezsim_new_sim_form", render_values)
