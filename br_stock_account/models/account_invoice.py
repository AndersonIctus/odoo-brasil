# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    @api.depends('invoice_line_ids.price_subtotal',
                 'invoice_line_ids.price_total',
                 'tax_line_ids.amount',
                 'currency_id', 'company_id')
    def _compute_amount(self):
        super(AccountInvoice, self)._compute_amount()
        lines = self.invoice_line_ids

        self.total_seguro = sum(l.valor_seguro for l in lines)
        self.total_frete = sum(l.valor_frete for l in lines)
        self.total_despesas = sum(l.outras_despesas for l in lines)
        self.amount_total = self.total_bruto - self.total_desconto + \
            self.total_tax + self.total_frete + self.total_seguro + \
            self.total_despesas
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = self.amount_total * sign
        self.amount_total_signed = self.amount_total * sign

    total_seguro = fields.Float(
        string='Seguro ( + )', digits=dp.get_precision('Account'),
        compute="_compute_amount")
    total_despesas = fields.Float(
        string='Despesas ( + )', digits=dp.get_precision('Account'),
        compute="_compute_amount")
    total_frete = fields.Float(
        string='Frete ( + )', digits=dp.get_precision('Account'),
        compute="_compute_amount")

    carrier_name = fields.Char('Transportadora', size=32)
    vehicle_plate = fields.Char('Placa do Veiculo', size=7)
    vehicle_state_id = fields.Many2one('res.country.state', 'UF da Placa')
    vehicle_city_id = fields.Many2one(
        'res.state.city',
        'Municipio',
        domain="[('state_id', '=', vehicle_state_id)]")

    weight = fields.Float(
        string='Gross weight', states={'draft': [('readonly', False)]},
        help="The gross weight in Kg.", readonly=True)
    weight_net = fields.Float(
        'Net weight', help="The net weight in Kg.",
        readonly=True, states={'draft': [('readonly', False)]})
    number_of_packages = fields.Integer(
        'Volume', readonly=True, states={'draft': [('readonly', False)]})
    kind_of_packages = fields.Char(
        'Espécie', size=60, readonly=True, states={
            'draft': [
                ('readonly', False)]})
    brand_of_packages = fields.Char(
        'Brand', size=60, readonly=True, states={
            'draft': [
                ('readonly', False)]})
    notation_of_packages = fields.Char(
        'Numeração', size=60, readonly=True, states={
            'draft': [
                ('readonly', False)]})

    # Exportação
    uf_saida_pais_id = fields.Many2one(
        'res.country.state', domain=[('country_id.code', '=', 'BR')],
        string="UF Saída do País")
    local_embarque = fields.Char('Local de Embarque', size=60)
    local_despacho = fields.Char('Local despacho', size=60)

    def _prepare_edoc_vals(self, inv):
        res = super(AccountInvoice, self)._prepare_edoc_vals(inv)
        res['valor_frete'] = inv.total_frete
        res['valor_despesas'] = inv.total_despesas
        res['valor_seguro'] = inv.total_seguro

        res['uf_saida_pais_id'] = inv.uf_saida_pais_id.id
        res['local_embarque'] = inv.local_embarque
        res['local_despacho'] = inv.local_despacho
        # TODO Passar as informações de transporte

        return res

    def _prepare_edoc_item_vals(self, invoice_line):
        vals = super(AccountInvoice, self).\
            _prepare_edoc_item_vals(invoice_line)
        vals['frete'] = invoice_line.valor_frete
        vals['seguro'] = invoice_line.valor_seguro
        vals['outras_despesas'] = invoice_line.outras_despesas
        return vals


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    def _prepare_tax_context(self):
        res = super(AccountInvoiceLine, self)._prepare_tax_context()
        res.update({
            'valor_frete': self.valor_frete,
            'valor_seguro': self.valor_seguro,
            'outras_despesas': self.outras_despesas,
        })
        return res

    @api.one
    @api.depends('valor_frete', 'valor_seguro', 'outras_despesas')
    def _compute_price(self):
        super(AccountInvoiceLine, self)._compute_price()

        total = self.valor_bruto - self.valor_desconto + self.valor_frete + \
            self.valor_seguro + self.outras_despesas
        self.update({'price_total': total})

    valor_frete = fields.Float(
        '(+) Frete', digits=dp.get_precision('Account'), default=0.00)
    valor_seguro = fields.Float(
        '(+) Seguro', digits=dp.get_precision('Account'), default=0.00)
    outras_despesas = fields.Float(
        '(+) Despesas', digits=dp.get_precision('Account'), default=0.00)
